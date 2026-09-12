from uuid import UUID

import httpx
import pytest

from app import __version__
from app.core.constants import REQUEST_ID_HEADER
from app.llm.fake import FakeLLMClient

pytestmark = pytest.mark.anyio


async def test_health_uses_public_versioned_contract(
    client: httpx.AsyncClient, fake_llm: FakeLLMClient
) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    request_id = response.headers[REQUEST_ID_HEADER]
    assert UUID(request_id)
    assert body == {
        "success": True,
        "data": {"status": "healthy", "version": __version__},
        "request_id": request_id,
    }
    assert fake_llm.call_count == 0


async def test_health_reuses_a_valid_request_id(client: httpx.AsyncClient) -> None:
    supplied = "A5F43136-35C5-4AB3-B1D0-CB61F0E67A8B"
    expected = str(UUID(supplied))

    response = await client.get(
        "/api/v1/health", headers={REQUEST_ID_HEADER: supplied}
    )

    assert response.headers[REQUEST_ID_HEADER] == expected
    assert response.json()["request_id"] == expected


async def test_health_replaces_an_invalid_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health", headers={REQUEST_ID_HEADER: "not-a-uuid"}
    )

    generated = response.headers[REQUEST_ID_HEADER]
    assert UUID(generated)
    assert generated != "not-a-uuid"
    assert response.json()["request_id"] == generated


async def test_unversioned_health_route_is_not_exposed(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/health")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]
