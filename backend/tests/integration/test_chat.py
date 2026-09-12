import asyncio
from collections.abc import Sequence
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.core.constants import REQUEST_ID_HEADER
from app.core.errors import ModelUnavailableError
from app.db.models import Conversation, User
from app.llm.base import LLMMessage
from app.llm.fake import FakeLLMClient
from app.schemas.chat import CHAT_DISCLAIMER

pytestmark = pytest.mark.anyio


async def _create_user_token(
    client: httpx.AsyncClient,
    *,
    suffix: str = "one",
) -> str:
    password = "safe-test-password-123"
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"user_{suffix}",
            "email": f"user_{suffix}@example.com",
            "password": password,
        },
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"login": f"user_{suffix}", "password": password},
    )
    assert login.status_code == 200
    return login.json()["data"]["access_token"]


class RecordingFakeLLM(FakeLLMClient):
    def __init__(self) -> None:
        super().__init__(response="  审慎的一般法律信息。  ")
        self.messages: Sequence[LLMMessage] = ()

    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        self.messages = tuple(messages)
        return await super().complete(messages)


class FailingFakeLLM(FakeLLMClient):
    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        del messages
        self.call_count += 1
        raise ModelUnavailableError()


class SlowFakeLLM(FakeLLMClient):
    async def complete(self, messages: Sequence[LLMMessage]) -> str:
        del messages
        self.call_count += 1
        await asyncio.sleep(1)
        return self.response


async def test_chat_requires_bearer_before_calling_model(
    client: httpx.AsyncClient,
    fake_llm: FakeLLMClient,
) -> None:
    response = await client.post(
        "/api/v1/chat/send",
        json={"message": "劳动争议如何处理？"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert response.headers["www-authenticate"] == "Bearer"
    assert fake_llm.call_count == 0


async def test_authenticated_chat_uses_llm_contract_and_persists_only_owner(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    token = await _create_user_token(client)
    recording_llm = RecordingFakeLLM()
    app.state.llm_client = recording_llm
    request_id = str(uuid4())

    response = await client.post(
        "/api/v1/chat/send",
        headers={
            "Authorization": f"Bearer {token}",
            REQUEST_ID_HEADER: request_id,
        },
        json={"message": "  公司拖欠工资，我应准备哪些材料？  "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER] == request_id
    assert body["data"]["response"] == "审慎的一般法律信息。"
    assert body["data"]["intent"] == "qa"
    assert body["data"]["sources"] == []
    assert body["data"]["missing_fields"] == []
    assert body["data"]["warnings"][0] == CHAT_DISCLAIMER
    assert any("未接入法律资料检索" in item for item in body["data"]["warnings"])
    assert any("不保存消息正文" in item for item in body["data"]["warnings"])
    assert recording_llm.call_count == 1
    assert recording_llm.messages[0].role == "system"
    assert "不得编造" in recording_llm.messages[0].content
    assert recording_llm.messages[1] == LLMMessage(
        role="user", content="公司拖欠工资，我应准备哪些材料？"
    )

    session_id = UUID(body["data"]["session_id"])
    with app.state.database.session() as session:
        conversation = session.get(Conversation, session_id)
        user = session.scalar(select(User))
        assert conversation is not None
        assert user is not None
        assert conversation.user_id == user.id
        assert conversation.title == "新咨询"


async def test_chat_logs_do_not_contain_token_or_message(
    client: httpx.AsyncClient,
    caplog,
) -> None:
    token = await _create_user_token(client)
    marker = "unique-private-question-marker-20260912"

    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": marker},
    )

    assert response.status_code == 200
    assert token not in caplog.text
    assert marker not in caplog.text


async def test_existing_session_is_reused_only_by_its_owner(
    client: httpx.AsyncClient,
    fake_llm: FakeLLMClient,
) -> None:
    owner_token = await _create_user_token(client, suffix="owner")
    other_token = await _create_user_token(client, suffix="other")
    created = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"message": "第一次咨询"},
    )
    assert created.status_code == 200
    session_id = created.json()["data"]["session_id"]
    assert fake_llm.call_count == 1

    continued = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"message": "继续咨询", "session_id": session_id},
    )
    assert continued.status_code == 200
    assert continued.json()["data"]["session_id"] == session_id
    assert fake_llm.call_count == 2

    forbidden = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"message": "尝试访问其他用户会话", "session_id": session_id},
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert fake_llm.call_count == 2


async def test_unknown_session_is_rejected_before_model_call(
    client: httpx.AsyncClient,
    fake_llm: FakeLLMClient,
) -> None:
    token = await _create_user_token(client)
    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "继续咨询", "session_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert fake_llm.call_count == 0


async def test_model_failure_does_not_leave_empty_session(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    token = await _create_user_token(client)
    app.state.llm_client = FailingFakeLLM()

    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "模型失败场景"},
    )

    assert response.status_code == 424
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0


async def test_outer_timeout_is_mapped_and_does_not_create_session(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    token = await _create_user_token(client)
    app.state.llm_client = SlowFakeLLM()
    object.__setattr__(app.state.settings, "deepseek_timeout_seconds", 0.01)

    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "超时场景"},
    )

    assert response.status_code == 424
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0


async def test_document_parameters_are_not_silently_ignored(
    client: httpx.AsyncClient,
    fake_llm: FakeLLMClient,
) -> None:
    token = await _create_user_token(client)
    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "生成起诉状",
            "document_type": "civil_complaint",
            "document_params": {"plaintiff": "测试当事人"},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert fake_llm.call_count == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "   "},
        {"message": "x" * 4001},
        {"message": "有效问题", "unexpected": True},
        {"message": "有效问题", "session_id": "not-a-uuid"},
        {"message": "有效问题", "document_type": "pdf"},
    ],
)
async def test_chat_rejects_invalid_input_without_calling_model(
    client: httpx.AsyncClient,
    fake_llm: FakeLLMClient,
    payload: dict[str, object],
) -> None:
    token = await _create_user_token(client)
    response = await client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert fake_llm.call_count == 0
