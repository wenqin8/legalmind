"""Shortest safe synchronous legal-question flow for week 1."""

from uuid import UUID, uuid4

from anyio import fail_after
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthenticatedUser
from app.core.config import Settings
from app.core.errors import (
    AppError,
    DatabaseUnavailableError,
    ModelUnavailableError,
    ResourceNotFoundError,
)
from app.db.models import Conversation
from app.db.session import Database
from app.llm.base import LLMClient, LLMMessage
from app.schemas.chat import (
    CHAT_DISCLAIMER,
    NO_CONTEXT_WARNING,
    NO_RETRIEVAL_WARNING,
    ChatData,
    ChatRequest,
)

SYSTEM_PROMPT = """你是面向中国大陆法律场景的法律信息助手。
当前阶段尚未连接法律法规或案例检索库，只能提供一般法律信息和办事思路。
首批范围仅包括婚姻家庭、劳动争议、交通事故和合同纠纷；领域之外的问题须明确说明覆盖有限，并给出保守的一般提示。
不得声称已经核验现行法，不得编造法律条文编号、案号、法院、裁判结果或资料来源。
缺少必要事实时应明确说明需要补充哪些信息；涉及人身安全、紧急处置或可能临近法定期限时，应优先建议联系有关机关或执业律师。
不要索取身份证号码、银行卡号、完整住址等非必要敏感信息。
请使用简洁、审慎的中文回答。通用免责声明由界面统一展示，不要在正文重复；若当前问题存在具体风险，仍应直接说明。"""


async def answer_chat(
    payload: ChatRequest,
    *,
    current_user: AuthenticatedUser,
    llm_client: LLMClient,
    database: Database,
    settings: Settings,
) -> ChatData:
    """Generate one answer and persist only its session ownership."""

    # Keep the authenticated identity explicit at the service boundary.
    if not isinstance(current_user.id, UUID):  # pragma: no cover - defensive boundary
        raise AppError(status_code=401, code="AUTH_REQUIRED", message="需要登录后才能访问")

    if payload.document_type is not None or payload.document_params is not None:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="当前问答接口暂不支持文书生成参数",
        )

    session_id, is_new_session = await run_in_threadpool(
        _resolve_session,
        database,
        current_user.id,
        payload.session_id,
    )

    try:
        timeout_buffer = min(5.0, max(0.1, settings.deepseek_timeout_seconds * 0.1))
        with fail_after(settings.deepseek_timeout_seconds + timeout_buffer):
            answer = await llm_client.complete(
                [
                    LLMMessage(role="system", content=SYSTEM_PROMPT),
                    LLMMessage(role="user", content=payload.message),
                ]
            )
    except TimeoutError as exc:
        raise ModelUnavailableError() from exc
    normalized_answer = answer.strip()
    if not normalized_answer or len(normalized_answer) > 20000:
        raise ModelUnavailableError()

    if is_new_session:
        await run_in_threadpool(
            _create_session,
            database,
            current_user.id,
            session_id,
        )

    return ChatData(
        response=normalized_answer,
        intent="qa",
        sources=[],
        session_id=session_id,
        missing_fields=[],
        warnings=[CHAT_DISCLAIMER, NO_RETRIEVAL_WARNING, NO_CONTEXT_WARNING],
    )


def _resolve_session(
    database: Database,
    user_id: UUID,
    requested_session_id: UUID | None,
) -> tuple[UUID, bool]:
    if requested_session_id is None:
        return uuid4(), True

    try:
        with database.session() as session:
            owned_session_id = session.scalar(
                select(Conversation.id).where(
                    Conversation.id == requested_session_id,
                    Conversation.user_id == user_id,
                )
            )
            if owned_session_id is None:
                raise ResourceNotFoundError()
            return owned_session_id, False
    except ResourceNotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def _create_session(database: Database, user_id: UUID, session_id: UUID) -> None:
    try:
        with database.session() as session:
            session.add(
                Conversation(
                    id=session_id,
                    user_id=user_id,
                    title="新咨询",
                )
            )
            session.commit()
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


async def delete_chat_session(
    database: Database,
    *,
    user_id: UUID,
    session_id: UUID,
) -> None:
    """Delete one conversation only when it belongs to the authenticated user."""

    await run_in_threadpool(_delete_session, database, user_id, session_id)


def _delete_session(database: Database, user_id: UUID, session_id: UUID) -> None:
    try:
        with database.session() as session:
            conversation = session.scalar(
                select(Conversation).where(
                    Conversation.id == session_id,
                    Conversation.user_id == user_id,
                )
            )
            if conversation is None:
                raise ResourceNotFoundError()
            session.delete(conversation)
            session.commit()
    except ResourceNotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc
