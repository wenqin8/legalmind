import logging
from typing import Annotated, Literal

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.constants import REQUEST_ID_HEADER
from app.core.errors import AppError

pytestmark = pytest.mark.anyio


class NumberPayload(BaseModel):
    value: int


class CatPayload(BaseModel):
    kind: Literal["cat"]


class DogPayload(BaseModel):
    kind: Literal["dog"]


class DiscriminatedPayload(BaseModel):
    item: Annotated[CatPayload | DogPayload, Field(discriminator="kind")]


def _add_error_routes(app: FastAPI) -> None:
    @app.get("/api/v1/_test/app-error")
    async def app_error() -> None:
        raise AppError(
            status_code=409,
            code="TEST_CONFLICT",
            message="测试冲突",
            details={"field": "name"},
        )

    @app.post("/api/v1/_test/validation")
    async def validation(_: NumberPayload) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/_test/unhandled")
    async def unhandled() -> None:
        raise RuntimeError("top-secret-upstream-detail")

    @app.post("/api/v1/_test/discriminated")
    async def discriminated(_: DiscriminatedPayload) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/_test/auth-required")
    async def auth_required() -> None:
        raise HTTPException(
            status_code=401,
            detail="internal-auth-detail",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def test_app_error_uses_uniform_envelope(app: FastAPI) -> None:
    _add_error_routes(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/_test/app-error")

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "TEST_CONFLICT",
        "message": "测试冲突",
        "details": {"field": "name"},
    }
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]


async def test_validation_error_does_not_echo_submitted_value(app: FastAPI) -> None:
    _add_error_routes(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/_test/validation", json={"value": "top-secret-input"}
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["fields"][0]["field"] == "body.value"
    assert "top-secret-input" not in response.text
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]


async def test_unhandled_error_is_sanitized(app: FastAPI, caplog) -> None:
    _add_error_routes(app)
    caplog.set_level(logging.ERROR, logger="app.errors")
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/_test/unhandled")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "INTERNAL_ERROR",
        "message": "服务暂时不可用，请稍后重试",
        "details": None,
    }
    assert "top-secret-upstream-detail" not in response.text
    assert "top-secret-upstream-detail" not in caplog.text
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]


async def test_unhandled_error_retains_cors_headers(app: FastAPI) -> None:
    _add_error_routes(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/_test/unhandled",
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]


async def test_method_not_allowed_is_wrapped(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert "GET" in response.headers["allow"]


async def test_validation_error_does_not_echo_union_tag(app: FastAPI) -> None:
    _add_error_routes(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/_test/discriminated",
            json={"item": {"kind": "top-secret-input"}},
        )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "body.item"
    assert "top-secret-input" not in response.text


async def test_auth_required_preserves_protocol_header(app: FastAPI) -> None:
    _add_error_routes(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/_test/auth-required")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert response.headers["www-authenticate"] == "Bearer"
