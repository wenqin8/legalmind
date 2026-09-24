import asyncio
import json
from pathlib import Path

import httpx
import pytest
from anyio import fail_after

from app.rag.legal_catalog import import_catalog, load_catalog
from tests.agent_helpers import configure_agent
from tests.integration.test_chat import _create_user_token
from tests.integration.test_live_stream import live_server
from tests.integration.test_multiturn_laws import ScriptedLLM

pytestmark = pytest.mark.anyio


class AuditedStreamLLM(ScriptedLLM):
    def __init__(self):
        super().__init__()
        self.checked = asyncio.Event()
        self.resume = asyncio.Event()
        self.closed = asyncio.Event()
        self.completed = False
        self.reject = False

    async def complete(self, messages):
        if messages[0].content.startswith('TASK:GROUNDING'):
            self.checked.set()
            if self.reject:
                data = json.loads(messages[1].content)
                return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported', 'supports': []}
                                             for u in data['units']]})
        return await super().complete(messages)

    async def stream(self, messages):
        try:
            yield '结论\n可按提供的依据核对主张[S1]。\n\n'
            await self.resume.wait()
            yield '风险\n需要核对事实。\n\n下一步\n整理材料。'
            self.completed = True
        finally:
            self.closed.set()


async def setup(app, client):
    configure_agent(app)
    import_catalog(app.state.database, load_catalog(Path('data/legal/verified_provisions.jsonl')))
    model = AuditedStreamLLM()
    app.state.llm_client = model
    token = await _create_user_token(client)
    return model, {'Authorization': f'Bearer {token}'}


PAYLOAD = {'message': 'facts=公司拖欠工资；event_date=2025年6月1日；context=有劳动合同'}


async def test_official_paragraph_arrives_after_audit_before_generation_completion(app, client):
    model, headers = await setup(app, client)
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=10) as remote:
        async with remote.stream('POST', '/api/v1/chat/stream', headers=headers, json=PAYLOAD) as response:
            lines = []
            async for line in response.aiter_lines():
                lines.append(line)
                if line == 'event: content' and not model.resume.is_set():
                    assert model.checked.is_set() and not model.completed
                    model.resume.set()
            assert any('"success":true' in line for line in lines)
    assert model.closed.is_set() and not app.state.session_store.locks


async def test_rejected_official_paragraph_never_reaches_client_or_history(app, client):
    model, headers = await setup(app, client)
    model.reject = True
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=10) as remote:
        response = await remote.post('/api/v1/chat/stream', headers=headers, json=PAYLOAD)
        assert 'event: content' not in response.text
        assert '"success":false' in response.text and 'event: error' in response.text
    assert not app.state.session_store.rows and not app.state.session_store.locks
    assert model.closed.is_set()


async def test_disconnect_after_verified_paragraph_cancels_without_saving(app, client):
    model, headers = await setup(app, client)
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=10) as remote:
        async with remote.stream('POST', '/api/v1/chat/stream', headers=headers, json=PAYLOAD) as response:
            async for line in response.aiter_lines():
                if line == 'event: content':
                    assert model.checked.is_set()
                    break
        with fail_after(5):
            await model.closed.wait()
            while app.state.session_store.locks:
                await asyncio.sleep(.01)
    assert not app.state.session_store.rows and not model.completed


@pytest.mark.parametrize('endpoint', ['send', 'stream'])
async def test_extraction_outage_is_an_error_not_a_saved_insufficient_answer(app, client, endpoint):
    from app.core.errors import ModelUnavailableError
    model, headers = await setup(app, client)
    original = model.complete
    model.resume.set()
    async def unavailable(messages):
        if messages[0].content.startswith('TASK:EXTRACT'):
            raise ModelUnavailableError()
        return await original(messages)
    model.complete = unavailable
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=10) as remote:
        response = await remote.post('/api/v1/chat/' + endpoint, headers=headers, json=PAYLOAD)
    if endpoint == 'send':
        assert response.status_code == 424
        assert response.json()['error']['code'] == 'MODEL_UNAVAILABLE'
    else:
        assert 'event: error' in response.text and '"success":false' in response.text
        assert 'event: content' not in response.text
    assert not app.state.session_store.rows and not app.state.session_store.locks
