import httpx
import pytest
from app.main import create_app


@pytest.mark.anyio
async def test_auth_limit_is_safe_and_does_not_block_health_or_preflight(settings, app):
    application = create_app(settings.model_copy(update={'auth_rate_limit_per_minute': 2}),
                             database=app.state.database, session_store=app.state.session_store)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url='http://test') as client:
        for _ in range(2):
            assert (await client.post('/api/v1/auth/login', json={})).status_code == 422
        response = await client.post('/api/v1/auth/login', json={'password': 'private'})
        assert response.status_code == 429
        assert response.json()['error']['code'] == 'RATE_LIMITED'
        assert response.json()['request_id'] == response.headers['x-request-id']
        assert 'private' not in response.text
        assert int(response.headers['retry-after']) > 0
        assert (await client.get('/api/v1/health')).status_code == 200
        assert (await client.options('/api/v1/auth/login', headers={'Origin':'http://localhost:5173', 'Access-Control-Request-Method':'POST'})).status_code == 200
        assert (await client.get('/api/v1/documents/templates')).status_code == 401
