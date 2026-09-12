"""Request tracing and safe access logging."""

import logging
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import REQUEST_ID_HEADER
from app.core.errors import error_response, get_request_id
from app.core.logging import request_id_context

logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.errors")


def normalize_request_id(candidate: str | None) -> str:
    if candidate:
        try:
            return str(UUID(candidate))
        except (ValueError, AttributeError):
            pass
    return str(uuid4())


class RequestContextMiddleware:
    """Attach a request ID and emit one access record per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = normalize_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        started = perf_counter()
        status_code = 500
        response_completed = False

        async def send_with_context(message: Message) -> None:
            nonlocal response_completed, status_code
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
                await send(message)
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                await send(message)
                if not message.get("more_body", False):
                    response_completed = True
            elif message["type"] == "http.response.pathsend":
                await send(message)
                response_completed = True
            else:
                await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            fastapi_scope = scope.get("fastapi", {})
            route_context = (
                fastapi_scope.get("effective_route_context")
                if isinstance(fastapi_scope, dict)
                else None
            )
            route = scope.get("route")
            path = (
                getattr(route_context, "path_format", None)
                or getattr(route, "path_format", None)
                or "<unmatched>"
            )
            user_id = scope.get("state", {}).get("user_id")
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": scope.get("method", "-"),
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "user_id": str(user_id) if user_id else None,
                    "response_completed": response_completed,
                },
            )
            request_id_context.reset(token)


class UnhandledExceptionMiddleware:
    """Convert unexpected failures before CORS processes the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def track_response_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, track_response_start)
        except Exception as exc:
            request = Request(scope, receive=receive)
            request_id = get_request_id(request)
            error_logger.error(
                "unhandled_exception",
                extra={
                    "event": "unhandled_exception",
                    "request_id": request_id,
                    "exception_type": type(exc).__name__,
                },
            )
            if response_started:
                raise
            response = error_response(
                request,
                status_code=500,
                code="INTERNAL_ERROR",
                message="服务暂时不可用，请稍后重试",
            )
            await response(scope, receive, send)
