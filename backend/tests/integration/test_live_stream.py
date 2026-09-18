"""Real loopback HTTP verifies timing and disconnects, not buffered ASGI output."""

import asyncio
from contextlib import asynccontextmanager
import socket

import httpx
import pytest
import uvicorn
from anyio import fail_after

from tests.agent_helpers import AgentLLM, configure_agent
from tests.integration.test_chat import _create_user_token

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def live_server(app):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="critical", access_log=False))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        with fail_after(10):
            while not server.started:
                if task.done():
                    await task
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        try:
            with fail_after(10):
                await task
        finally:
            listener.close()


class PausedLLM(AgentLLM):
    def __init__(self):
        super().__init__()
        self.resume = asyncio.Event()
        self.closed = asyncio.Event()
        self.completed = False
        self.started = asyncio.Event()

    async def stream(self, messages):
        try:
            self.started.set()
            yield "结论\n先根据演示材料整理证据[S1]。\n\n"
            await self.resume.wait()
            yield "风险\n法律依据不足。\n\n下一步\n核对材料。"
            self.completed = True
        finally:
            self.closed.set()


async def test_first_paragraph_arrives_before_model_completion(app, client):
    configure_agent(app)
    token = await _create_user_token(client)
    model = PausedLLM()
    app.state.llm_client = model
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=5) as remote:
        async with remote.stream("POST", "/api/v1/chat/stream", headers={"Authorization": f"Bearer {token}"}, json={"message": "拖欠工资怎么办"}) as response:
            assert response.status_code == 200
            lines = []
            async for line in response.aiter_lines():
                lines.append(line)
                if line == "event: content" and not model.resume.is_set():
                    assert not model.completed
                    model.resume.set()
        assert 'event: done' in lines
        assert any('"success":true' in line for line in lines)
    assert model.completed
    assert len(next(iter(app.state.session_store.rows.values())).messages) == 2
    assert not app.state.session_store.locks


async def test_client_disconnect_cancels_upstream_and_keeps_existing_history(app, client):
    configure_agent(app)
    token = await _create_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    first = await client.post("/api/v1/chat/send", headers=headers, json={"message": "第一次咨询"})
    sid = first.json()["data"]["session_id"]
    before = dict(app.state.session_store.rows)
    model = PausedLLM()
    app.state.llm_client = model
    async with live_server(app) as url, httpx.AsyncClient(base_url=url, timeout=5) as remote:
        async with remote.stream("POST", "/api/v1/chat/stream", headers=headers, json={"message": "继续咨询", "session_id": sid}) as response:
            async for line in response.aiter_lines():
                if line == "event: content":
                    break
        with fail_after(5):
            await model.closed.wait()
            while app.state.session_store.locks:
                await asyncio.sleep(0.01)
    assert not model.completed
    assert app.state.session_store.rows == before


async def test_parallel_generation_and_delete_conflict_only_on_same_session(app, client):
    configure_agent(app)
    token = await _create_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    initial = await client.post("/api/v1/chat/send", headers=headers, json={"message": "初次咨询"})
    sid = initial.json()["data"]["session_id"]
    model = PausedLLM()
    app.state.llm_client = model
    active = asyncio.create_task(client.post("/api/v1/chat/send", headers=headers, json={"message": "继续分析", "session_id": sid}))
    try:
        with fail_after(5):
            await model.started.wait()
        busy = await client.post("/api/v1/chat/send", headers=headers, json={"message": "并发追问", "session_id": sid})
        assert busy.status_code == 409 and busy.json()["error"]["code"] == "SESSION_BUSY"
        assert (await client.delete(f"/api/v1/chat/history/{sid}", headers=headers)).status_code == 409
        separate = await client.post("/api/v1/chat/send", headers=headers, json={"message": "查找工资案例"})
        assert separate.status_code == 200
        assert separate.json()["data"]["session_id"] != sid
    finally:
        model.resume.set()
        completed = await active
    assert completed.status_code == 200
    assert not app.state.session_store.locks


async def test_disconnect_during_legal_answer_preserves_collected_facts(app, client):
    from pathlib import Path
    from app.rag.legal_catalog import import_catalog, load_catalog
    from tests.integration.test_multiturn_laws import ScriptedLLM
    configure_agent(app)
    import_catalog(app.state.database, load_catalog(Path('data/legal/verified_provisions.jsonl')))
    class PausedLegal(ScriptedLLM):
        def __init__(self):
            super().__init__()
            self.closed = asyncio.Event()
        async def stream(self, messages):
            try:
                yield '结论\n请核对条文适用条件[S1]。\n\n'
                await asyncio.Event().wait()
            finally:
                self.closed.set()
    model = PausedLegal()
    app.state.llm_client = model
    token = await _create_user_token(client)
    headers = {'Authorization':f'Bearer {token}'}
    initial = await client.post('/api/v1/chat/send',headers=headers,json={'message':'facts=公司拖欠工资'})
    sid = initial.json()['data']['session_id']
    before = dict(app.state.session_store.rows)
    async with live_server(app) as url, httpx.AsyncClient(base_url=url,timeout=5) as remote:
        async with remote.stream('POST','/api/v1/chat/stream',headers=headers,json={'message':'event_date=2025年6月1日；context=已有劳动合同','session_id':sid}) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line == 'event: content':
                    break
        with fail_after(5):
            await model.closed.wait()
            while app.state.session_store.locks:
                await asyncio.sleep(.01)
    assert app.state.session_store.rows == before
