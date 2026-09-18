import asyncio
import json
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import DatabaseUnavailableError, ModelUnavailableError
from app.db.models import Conversation, User, GeneratedDocument
from app.schemas.documents import TEMPLATES
from app.services.session_store import HistorySnapshot
from tests.agent_helpers import AgentLLM, configure_agent

pytestmark = pytest.mark.anyio


async def _create_user_token(client, *, suffix="one"):
    password = "safe-test-password-123"
    registered = await client.post("/api/v1/auth/register", json={"username": f"user_{suffix}", "email": f"user_{suffix}@example.com", "password": password})
    assert registered.status_code == 201
    result = await client.post("/api/v1/auth/login", json={"login": f"user_{suffix}", "password": password})
    assert result.status_code == 200
    return result.json()["data"]["access_token"]


@pytest.fixture(autouse=True)
def agent_setup(app):
    configure_agent(app)


async def send(client, headers, message="拖欠工资怎么办", session_id=None, path="send", **extra):
    return await client.post(f"/api/v1/chat/{path}", headers=headers, json={"message": message, "session_id": session_id, **extra})


async def auth(client, suffix="one"):
    return {"Authorization": f"Bearer {await _create_user_token(client, suffix=suffix)}"}


async def test_auth_and_ownership_precede_model_and_redis(client, app):
    assert (await send(client, {})).status_code == 401
    owner, other = await auth(client), await auth(client, "other")
    created = await send(client, owner)
    assert created.status_code == 200
    sid = created.json()["data"]["session_id"]
    count = app.state.llm_client.call_count
    app.state.session_store.available = False
    for session_id in (sid, str(uuid4())):
        assert (await send(client, other, session_id=session_id)).status_code == 404
        assert (await client.get(f"/api/v1/chat/history/{session_id}", headers=other)).status_code == 404
        assert (await client.delete(f"/api/v1/chat/history/{session_id}", headers=other)).status_code == 404
    assert app.state.llm_client.call_count == count


async def test_qa_sources_history_and_context_are_owned(client, app, caplog):
    headers = await auth(client)
    marker = "unique-private-question-marker"
    first = await send(client, headers, message=marker)
    assert first.status_code == 200
    data = first.json()["data"]
    assert data["intent"] == "qa"
    assert data["sources"][0]["date"] is None
    assert data["sources"][0]["sample_date"] is not None
    assert data["sources"][0]["is_synthetic"] is True
    assert "不是真实判例" in data["response"]
    sid = data["session_id"]
    second = await send(client, headers, message="需要哪些证据", session_id=sid)
    assert second.status_code == 200
    qa_input = json.loads(app.state.llm_client.requests[-1][1].content)
    assert qa_input["history"][0]["content"] == marker
    history = (await client.get(f"/api/v1/chat/history/{sid}", headers=headers)).json()["data"]
    assert len(history["messages"]) == 4
    assert not history["history_expired"]
    await send(client, headers, message="一个新咨询")
    assert json.loads(app.state.llm_client.requests[-1][1].content)["history"] == []
    listing = (await client.get("/api/v1/chat/conversations?limit=1", headers=headers)).json()["data"]
    assert listing["total"] == 2 and len(listing["items"]) == 1
    assert marker not in caplog.text
    assert headers["Authorization"] not in caplog.text


async def test_expiration_retains_session_and_resets_context(client, app):
    headers = await auth(client)
    first = await send(client, headers)
    sid = first.json()["data"]["session_id"]
    key = next(iter(app.state.session_store.rows))
    old = app.state.session_store.rows[key]
    app.state.session_store.rows[key] = HistorySnapshot(old.messages, time.monotonic() - 1)
    history = (await client.get(f"/api/v1/chat/history/{sid}", headers=headers)).json()["data"]
    assert history["history_expired"] and history["messages"] == []
    continued = await send(client, headers, session_id=sid)
    assert continued.status_code == 200
    assert any("历史内容已过期" in item for item in continued.json()["data"]["warnings"])
    assert json.loads(app.state.llm_client.requests[-1][1].content)["history"] == []
    with app.state.database.session() as session:
        assert session.get(Conversation, UUID(sid)) is not None


async def test_delete_and_list_only_current_users_sessions(client, app):
    owner, other = await auth(client), await auth(client, "other")
    sid = (await send(client, owner)).json()["data"]["session_id"]
    assert (await client.get("/api/v1/chat/conversations", headers=other)).json()["data"]["total"] == 0
    assert (await client.delete(f"/api/v1/chat/history/{sid}", headers=owner)).status_code == 200
    assert not app.state.session_store.rows
    assert (await client.get(f"/api/v1/chat/history/{sid}", headers=owner)).status_code == 404


async def test_failure_timeout_invalid_citation_leave_no_session(client, app):
    headers = await auth(client)
    class Failing(AgentLLM):
        async def stream(self, messages):
            yield "结论\n不完整的片段。\n\n"
            raise ModelUnavailableError()
    app.state.llm_client = Failing()
    assert (await send(client, headers)).status_code == 424
    app.state.llm_client = AgentLLM()
    app.state.llm_client.response = "结论[S9]\n\n风险\n\n下一步"
    assert (await send(client, headers)).status_code == 424
    class Slow(AgentLLM):
        async def stream(self, messages):
            await asyncio.sleep(1)
            yield self.response
    app.state.llm_client = Slow()
    object.__setattr__(app.state.settings, "deepseek_timeout_seconds", 0.01)
    assert (await send(client, headers)).status_code == 424
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
    assert not app.state.session_store.rows
    assert not app.state.session_store.locks


async def test_empty_and_unrelated_evidence_is_conservative_success(client, app):
    headers = await auth(client)
    app.state.llm_client.selection = False
    response = await send(client, headers)
    assert response.status_code == 200
    assert response.json()["data"]["sources"] == []
    assert "不足" in response.json()["data"]["response"]
    assert app.state.llm_client.stream_calls == 0


@pytest.mark.parametrize("kind", list(TEMPLATES))
async def test_chat_document_branch_reports_missing_and_persists_downloadable_draft(client, app, kind):
    headers = await auth(client)
    missing = await send(client, headers, document_type=kind)
    assert missing.status_code == 200
    assert missing.json()["data"]["intent"] == "document"
    assert missing.json()["data"]["missing_fields"]
    params = {field.name: f"提供的{field.label}" for field in TEMPLATES[kind].fields}
    response = await send(client, headers, document_type=kind, document_params=params)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["document_id"] is None
    assert data["task"]["phase"] == "review"
    response = await send(client, headers, message="确认生成", session_id=data["session_id"], task_revision=data["task"]["revision"])
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["document_id"]
    assert (await client.get(f'/api/v1/documents/{data["document_id"]}/download', headers=headers)).status_code == 200


async def test_search_branch_uses_no_generation(client, app):
    headers = await auth(client)
    result = await send(client, headers, message="查找工资案例")
    assert result.json()["data"]["intent"] == "search"
    assert result.json()["data"]["sources"]
    assert app.state.llm_client.call_count == 0


async def test_session_busy_and_redis_unavailable_are_explicit(client, app):
    headers = await auth(client)
    sid = (await send(client, headers)).json()["data"]["session_id"]
    key = next(iter(app.state.session_store.rows))
    token = await app.state.session_store.acquire(key, 60)
    assert (await send(client, headers, session_id=sid)).status_code == 409
    assert (await client.delete(f"/api/v1/chat/history/{sid}", headers=headers)).status_code == 409
    await app.state.session_store.release(key, token)
    app.state.session_store.available = False
    for path in ("send", "stream"):
        result = await send(client, headers, path=path, session_id=sid)
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "SESSION_STORE_UNAVAILABLE"


async def test_failed_database_commit_compensates_messages_and_document(client, app, monkeypatch):
    headers = await auth(client)
    sid = (await send(client, headers)).json()["data"]["session_id"]
    before = dict(app.state.session_store.rows)
    def failure(*args):
        raise DatabaseUnavailableError()
    monkeypatch.setattr("app.services.chat.save_completion", failure)
    result = await send(client, headers, session_id=sid)
    assert result.status_code == 503
    assert app.state.session_store.rows == before
    params = {field.name: f"提供的{field.label}" for field in TEMPLATES["civil_complaint"].fields}
    draft = await send(client, headers, session_id=sid, document_type="civil_complaint", document_params=params)
    assert draft.status_code == 503
    assert app.state.session_store.rows == before
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(GeneratedDocument)) == 0
    monkeypatch.setattr("app.services.chat.delete_session", failure)
    assert (await client.delete(f"/api/v1/chat/history/{sid}", headers=headers)).status_code == 503
    assert app.state.session_store.rows == before


async def test_parameter_errors_before_stream_headers_and_failed_append_do_not_claim_success(client, app, monkeypatch):
    headers = await auth(client)
    result = await send(client, headers, path="stream", document_type="civil_complaint", document_params={"unknown": "x"})
    assert result.status_code == 422
    oversized = await send(client, headers, path="stream", document_type="civil_complaint", document_params={"plaintiff": "x" * 501})
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "VALIDATION_ERROR"
    from app.services.session_store import SessionStoreUnavailable
    original = app.state.session_store.append_pair
    async def write_then_fail(*args):
        await original(*args)
        raise SessionStoreUnavailable()
    monkeypatch.setattr(app.state.session_store, "append_pair", write_then_fail)
    failed = await send(client, headers, path="stream")
    assert '"success":false' in failed.text
    assert '"success":true' not in failed.text
    assert not app.state.session_store.rows
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0


async def test_sse_protocol_and_partial_failure(client, app):
    headers = await auth(client)
    response = await send(client, headers, path="stream")
    assert response.status_code == 200
    events = [block.splitlines() for block in response.text.strip().split("\n\n")]
    assert events[0][0] == "event: meta"
    assert events[-2][0] == "event: sources"
    assert events[-1][0] == "event: done"
    assert json.loads(events[-1][1][6:])["success"]
    assert all(len(event) == 2 for event in events)
    app.state.llm_client.response = "结论\n材料[S1]。\n\n风险\n未知[S9]。\n\n下一步\n核验。"
    response = await send(client, headers, path="stream")
    assert "event: error" in response.text
    assert '"success":false' in response.text
    assert "未知[S9]" not in response.text
    assert not app.state.session_store.locks


async def test_uncommitted_redis_tail_is_discarded_after_failed_compensation(client, app, monkeypatch):
    from app.services.session_store import SessionStoreUnavailable
    headers = await auth(client)
    sid = (await send(client, headers)).json()["data"]["session_id"]
    original_append = app.state.session_store.append_pair
    original_restore = app.state.session_store.restore
    async def append_then_fail(*args):
        await original_append(*args)
        raise SessionStoreUnavailable()
    async def cannot_restore(*args):
        raise SessionStoreUnavailable()
    monkeypatch.setattr(app.state.session_store, "append_pair", append_then_fail)
    monkeypatch.setattr(app.state.session_store, "restore", cannot_restore)
    assert (await send(client, headers, session_id=sid, message="失败轮次不应记住")).status_code == 503
    assert len(next(iter(app.state.session_store.rows.values())).messages) == 4
    monkeypatch.setattr(app.state.session_store, "append_pair", original_append)
    monkeypatch.setattr(app.state.session_store, "restore", original_restore)
    history = (await client.get(f"/api/v1/chat/history/{sid}", headers=headers)).json()["data"]
    assert len(history["messages"]) == 2
    assert "失败轮次不应记住" not in str(history)


@pytest.mark.parametrize("failure", ["truncation", "timeout", "store"])
async def test_stream_late_failures_keep_last_committed_context(client, app, monkeypatch, failure):
    from app.services.session_store import SessionStoreUnavailable
    headers = await auth(client)
    sid = (await send(client, headers)).json()["data"]["session_id"]
    before = dict(app.state.session_store.rows)
    if failure == "store":
        async def broken_append(*args):
            raise SessionStoreUnavailable()
        monkeypatch.setattr(app.state.session_store, "append_pair", broken_append)
        expected = "SESSION_STORE_UNAVAILABLE"
    else:
        class Interrupted(AgentLLM):
            async def stream(self, messages):
                yield "结论\n演示材料[S1]。\n\n"
                if failure == "timeout":
                    await asyncio.sleep(1)
                raise ModelUnavailableError()
        app.state.llm_client = Interrupted()
        if failure == "timeout":
            object.__setattr__(app.state.settings, "deepseek_timeout_seconds", 0.02)
        expected = "MODEL_UNAVAILABLE"
    response = await send(client, headers, path="stream", session_id=sid)
    assert response.status_code == 200
    assert "event: content" in response.text
    assert expected in response.text
    assert '"success":false' in response.text and '"success":true' not in response.text
    assert app.state.session_store.rows == before
    assert not app.state.session_store.locks


@pytest.mark.parametrize("payload", [{"message": ""}, {"message": "   "}, {"message": "x" * 4001}, {"message": "问题", "unexpected": True}, {"message": "问题", "session_id": "bad"}, {"message": "问题", "document_type": "pdf"}])
async def test_invalid_input_does_not_call_model(client, app, payload):
    headers = await auth(client)
    response = await client.post("/api/v1/chat/send", headers=headers, json=payload)
    assert response.status_code == 422
    assert app.state.llm_client.call_count == 0
