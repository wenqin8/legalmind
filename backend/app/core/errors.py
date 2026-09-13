"""Application errors and uniform FastAPI exception responses."""

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import REQUEST_ID_HEADER

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """A safe, user-facing application error."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = dict(details) if details is not None else None
        self.headers = dict(headers) if headers is not None else None


class ModelUnavailableError(AppError):
    """The configured model cannot currently complete the request."""

    def __init__(self) -> None:
        super().__init__(
            status_code=424,
            code="MODEL_UNAVAILABLE",
            message="模型服务暂时不可用，请稍后重试",
        )


class RetrievalUnavailableError(AppError):
    """The configured embedding or retrieval index cannot serve a query."""

    def __init__(self) -> None:
        super().__init__(
            status_code=424,
            code="RETRIEVAL_UNAVAILABLE",
            message="案例检索服务暂时不可用，请稍后重试",
        )


class AuthenticationRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="AUTH_REQUIRED",
            message="需要登录后才能访问",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="用户名、邮箱或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AccountAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="ACCOUNT_ALREADY_EXISTS",
            message="用户名或邮箱已被使用",
        )


class ResourceNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="RESOURCE_NOT_FOUND",
            message="请求的资源不存在",
        )


class DatabaseUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="DATABASE_UNAVAILABLE",
            message="数据库暂时不可用，请稍后重试",
        )


class AuthenticationUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="AUTH_UNAVAILABLE",
            message="登录服务尚未正确配置",
        )


def get_request_id(request: Request) -> str:
    """Get a normalized request ID without trusting arbitrary header text."""

    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return str(state_id)

    candidate = request.headers.get(REQUEST_ID_HEADER)
    if candidate:
        try:
            return str(UUID(candidate))
        except (ValueError, AttributeError):
            pass
    return str(uuid4())


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Mapping[str, Any] | list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    response_headers = dict(headers or {})
    response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "request_id": request_id,
        },
        headers=response_headers,
    )


def _declared_field_names(request: Request, location: str) -> set[str]:
    """Return only server-declared top-level input names for one location."""

    route = request.scope.get("route")
    if route is None:
        return set()
    if location == "body":
        body_field = getattr(route, "body_field", None)
        if body_field is None:
            return set()
        annotation = getattr(getattr(body_field, "field_info", None), "annotation", None)
        model_fields = getattr(annotation, "model_fields", None)
        if isinstance(model_fields, dict):
            return {
                str(getattr(field, "alias", None) or name)
                for name, field in model_fields.items()
            }
        return {
            str(value)
            for value in (
                getattr(body_field, "alias", None),
                getattr(body_field, "name", None),
            )
            if value
        }

    dependant = getattr(route, "dependant", None)
    parameter_group = {
        "query": "query_params",
        "path": "path_params",
        "header": "header_params",
        "cookie": "cookie_params",
    }.get(location)
    if dependant is None or parameter_group is None:
        return set()
    return {
        str(getattr(field, "alias", None) or getattr(field, "name", ""))
        for field in getattr(dependant, parameter_group, ())
    }


def _safe_validation_details(
    request: Request, exc: RequestValidationError
) -> list[dict[str, Any]]:
    """Remove submitted values and internal context from validation errors."""

    safe_details: list[dict[str, Any]] = []
    allowed_locations = {"body", "query", "path", "header", "cookie"}
    for error in exc.errors():
        location = error.get("loc", ())
        location_root = location[0] if location else None
        public_location = (
            location_root if location_root in allowed_locations else "request"
        )
        if len(location) > 1:
            candidate = str(location[1])
            if candidate in _declared_field_names(request, str(public_location)):
                public_location = f"{public_location}.{candidate}"
        internal_type = str(error.get("type", "invalid_value"))
        if internal_type == "missing":
            public_type, public_message = "missing", "必填字段缺失"
        elif internal_type == "json_invalid":
            public_type, public_message = "json_invalid", "请求 JSON 格式不正确"
        else:
            public_type, public_message = "invalid_value", "字段值不合法"
        safe_details.append(
            {
                "field": public_location,
                "message": public_message,
                "type": public_type,
            }
        )
    return safe_details


def register_exception_handlers(app: FastAPI) -> None:
    """Install exception handlers that preserve the public error contract."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="请求参数不正确",
            details={"fields": _safe_validation_details(request, exc)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            code, message = "RESOURCE_NOT_FOUND", "请求的资源不存在"
        elif exc.status_code == 405:
            code, message = "BAD_REQUEST", "请求方法不被允许"
        elif exc.status_code == 401:
            code, message = "AUTH_REQUIRED", "需要登录后才能访问"
        elif 400 <= exc.status_code < 500:
            code, message = "BAD_REQUEST", "请求无法处理"
        else:
            code, message = "INTERNAL_ERROR", "服务暂时不可用"
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            extra={
                "event": "unhandled_exception",
                "request_id": get_request_id(request),
                "exception_type": type(exc).__name__,
            },
        )
        return error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="服务暂时不可用，请稍后重试",
        )
