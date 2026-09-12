import httpx
import pytest

from app.core.constants import REQUEST_ID_HEADER

ALLOWED_ORIGIN = "http://localhost:5173"
pytestmark = pytest.mark.anyio


async def test_allowed_origin_preflight(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID,Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "X-Request-ID" in response.headers["access-control-allow-headers"]
    assert REQUEST_ID_HEADER in response.headers


async def test_actual_response_exposes_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health", headers={"Origin": ALLOWED_ORIGIN}
    )

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert REQUEST_ID_HEADER in response.headers["access-control-expose-headers"]
    assert "Content-Disposition" in response.headers["access-control-expose-headers"]


async def test_unknown_origin_is_not_allowed(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health", headers={"Origin": "https://untrusted.example"}
    )

    assert "access-control-allow-origin" not in response.headers
