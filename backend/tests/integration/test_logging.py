import json
import logging

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.core.logging import JsonFormatter, request_id_context

pytestmark = pytest.mark.anyio


async def test_access_log_is_structured_without_request_secrets(
    client: httpx.AsyncClient, caplog
) -> None:
    caplog.set_level(logging.INFO, logger="app.access")

    response = await client.get(
        "/api/v1/health",
        headers={
            "Authorization": "Bearer must-not-be-logged",
            "X-Debug-Secret": "must-not-be-logged",
        },
    )

    records = [
        record
        for record in caplog.records
        if record.name == "app.access" and record.getMessage() == "request_completed"
    ]
    assert len(records) == 1
    record = records[0]
    assert record.method == "GET"
    assert record.path == "/api/v1/health"
    assert record.status_code == 200
    assert record.request_id == response.headers["X-Request-ID"]
    assert record.duration_ms >= 0
    assert record.response_completed is True
    assert "must-not-be-logged" not in caplog.text


async def test_access_log_uses_route_template_for_dynamic_paths(
    app: FastAPI, caplog
) -> None:
    @app.get("/api/v1/_test/items/{item_id}")
    async def get_item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    caplog.set_level(logging.INFO, logger="app.access")
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/_test/items/private-resource-id")

    assert response.status_code == 200
    records = [
        record
        for record in caplog.records
        if record.name == "app.access" and record.getMessage() == "request_completed"
    ]
    assert len(records) == 1
    assert records[0].path == "/api/v1/_test/items/{item_id}"
    assert "private-resource-id" not in caplog.text


def test_http_client_request_logs_are_suppressed() -> None:
    for logger_name in ("httpx", "httpcore", "uvicorn.access"):
        assert logging.getLogger(logger_name).getEffectiveLevel() >= logging.WARNING


async def test_unmatched_path_content_is_not_logged(
    client: httpx.AsyncClient, caplog
) -> None:
    caplog.set_level(logging.INFO, logger="app.access")

    response = await client.get("/api/v1/private-user-content")

    assert response.status_code == 404
    records = [
        record
        for record in caplog.records
        if record.name == "app.access" and record.getMessage() == "request_completed"
    ]
    assert len(records) == 1
    assert records[0].path == "<unmatched>"
    assert "private-user-content" not in JsonFormatter().format(records[0])


def test_json_formatter_emits_machine_readable_safe_fields() -> None:
    record = logging.LogRecord(
        name="app.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-id"
    record.method = "GET"
    record.path = "/api/v1/health"
    record.status_code = 200
    record.response_completed = True

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "request-id"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["response_completed"] is True


async def test_stream_keeps_request_context_until_body_finishes(
    app: FastAPI, caplog
) -> None:
    @app.get("/api/v1/_test/stream")
    async def stream() -> StreamingResponse:
        async def chunks():
            assert request_id_context.get() != "-"
            yield "first"
            assert request_id_context.get() != "-"
            yield "second"

        return StreamingResponse(chunks(), media_type="text/plain")

    caplog.set_level(logging.INFO, logger="app.access")
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/_test/stream")

    assert response.text == "firstsecond"
    records = [
        record
        for record in caplog.records
        if record.name == "app.access" and record.getMessage() == "request_completed"
    ]
    assert len(records) == 1
    assert records[0].path == "/api/v1/_test/stream"
    assert records[0].response_completed is True
