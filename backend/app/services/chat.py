"""Owned conversation lifecycle with success-only history and graph execution."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from anyio import CancelScope, fail_after, lowlevel
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.agents.workflow import Emitter, build_workflow, discard_event
from app.core.config import Settings
from app.core.errors import AppError, ModelUnavailableError
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever
from app.repositories.conversations import resolve_session, get_commit_marker, save_completion, delete_session, list_sessions
from app.schemas.chat import ChatData, ChatRequest, ConversationMessage, ConversationsData, ConversationSummary, HistoryData
from app.services.session_store import HISTORY_EXPIRED_WARNING, HistorySnapshot, SessionStore, SessionStoreUnavailable, history_key
from app.schemas.documents import DocumentRequest
from app.services.documents import validate_parameters
from app.agents.tasks import action_for
import json

logger = logging.getLogger("app.chat")


def parse_history(snapshot: HistorySnapshot) -> list[ConversationMessage]:
    try:
        messages = [ConversationMessage.model_validate_json(value) for value in snapshot.messages]
        if len(messages) > 20 or len(messages) % 2 or any(message.role != ("user" if i % 2 == 0 else "assistant") for i, message in enumerate(messages)):
            raise ValueError("Invalid history order")
        if any(messages[i].turn_id != messages[i + 1].turn_id for i in range(0, len(messages), 2)):
            raise ValueError("Mismatched history pair")
        return messages
    except (ValueError, ValidationError) as exc:
        raise SessionStoreUnavailable() from exc


def bounded_context(messages: list[ConversationMessage]) -> list[ConversationMessage]:
    recent = messages[-10:]
    while recent and sum(len(message.content) for message in recent) > 12000:
        recent = recent[2:]
    return recent


@dataclass
class ChatLease:
    session_id: UUID
    user_id: UUID
    is_new: bool
    key: str
    token: str
    snapshot: HistorySnapshot


async def release_lease(store: SessionStore, lease: ChatLease) -> None:
    with CancelScope(shield=True):
        try:
            await store.release(lease.key, lease.token)
        except SessionStoreUnavailable:
            logger.warning("session_lock_release_failed", extra={"event": "session_lock_release_failed"})


async def prepare_chat(payload: ChatRequest, *, user_id: UUID, database: Database, store: SessionStore, settings: Settings) -> ChatLease:
    if payload.document_params is not None:
        params = payload.document_params
        if len(json.dumps(params, ensure_ascii=False).encode("utf-8")) > 20480 or any(not isinstance(value, str) for value in params.values()):
            raise AppError(status_code=422, code="VALIDATION_ERROR", message="文书参数不正确")
        if payload.document_type:
            try:
                validate_parameters(DocumentRequest(document_type=payload.document_type, parameters=params))
            except AppError as exc:
                if exc.code != "DOCUMENT_FIELDS_MISSING":
                    raise
    session_id, is_new = await run_in_threadpool(resolve_session, database, user_id, payload.session_id)
    key = history_key(user_id, session_id)
    token = await store.acquire(key, settings.deepseek_timeout_seconds + 20)
    lease = ChatLease(session_id, user_id, is_new, key, token, HistorySnapshot([], None))
    try:
        if not is_new:
            await run_in_threadpool(resolve_session, database, user_id, session_id)
        lease.snapshot = await store.snapshot(key, token)
        messages = parse_history(lease.snapshot)
        if messages:
            marker = None if is_new else await run_in_threadpool(get_commit_marker, database, user_id, session_id)
            end = next((i + 1 for i in range(len(messages) - 1, -1, -2) if marker is not None and messages[i].turn_id == marker), 0)
            if end != len(messages):
                # Ignore and remove Redis writes that never reached a relational commit,
                # including a crash or a failed compensation while Redis was offline.
                lease.snapshot = HistorySnapshot(lease.snapshot.messages[:end], lease.snapshot.expires_at)
                await store.restore(key, token, lease.snapshot)
        messages = parse_history(lease.snapshot)
        previous = messages[-1].task if messages else None
        effective_type = payload.document_type or (previous.document_type if previous and previous.kind == "document" else None)
        if payload.document_params is not None and effective_type:
            try:
                validate_parameters(DocumentRequest(document_type=effective_type, parameters=payload.document_params))
            except AppError as exc:
                if exc.code != "DOCUMENT_FIELDS_MISSING":
                    raise
        if payload.task_revision and (previous is None or previous.revision != payload.task_revision):
            raise AppError(status_code=409, code="TASK_CHANGED", message="任务摘要已更新或过期，请核对当前内容后再确认")
        if payload.task_action in {"confirm", "accept_changes", "reject_changes"} and (payload.document_params or payload.message.strip(" 。！!\n") not in {"确认生成", "确认摘要", "确认修改", "保留原值"}):
            raise AppError(status_code=422, code="VALIDATION_ERROR", message="确认操作不能同时修改参数，请先提交更正信息")
        return lease
    except BaseException:
        await release_lease(store, lease)
        raise


async def execute_chat(payload: ChatRequest, lease: ChatLease, *, request_id: UUID, database: Database,
                       store: SessionStore, settings: Settings, llm: LLMClient, retriever: HybridCaseRetriever,
                       emit: Emitter = discard_event) -> ChatData:
    committed = parse_history(lease.snapshot)
    history = bounded_context(committed)
    task = committed[-1].task if committed else None
    turn_id = uuid4()
    warnings = [HISTORY_EXPIRED_WARNING] if not lease.is_new and not lease.snapshot.messages else []
    try:
        with fail_after(settings.deepseek_timeout_seconds + min(5, max(0.1, settings.deepseek_timeout_seconds * 0.1))):
            graph = build_workflow(database, retriever, llm, emit)
            state = await graph.ainvoke({"request_id": request_id, "user_id": lease.user_id, "session_id": lease.session_id,
                                        "payload": payload, "conversation_messages": history, "warnings": warnings,
                                        "turn_id": turn_id, "task": task}, {"recursion_limit": 10})
            result = state["result"]
            now = datetime.now(timezone.utc)
            pair = [ConversationMessage(role="user", content=payload.message, created_at=now, turn_id=turn_id).model_dump_json(),
                    ConversationMessage(role="assistant", content=result.response, created_at=now, turn_id=turn_id, intent=result.intent,
                                        sources=result.sources, warnings=result.warnings, missing_fields=result.missing_fields,
                                        document_id=result.document_id, task=result.task).model_dump_json()]
            await lowlevel.checkpoint()
            # Only this short commit/compensation phase is shielded, never generation.
            with CancelScope(shield=True):
                try:
                    await store.append_pair(lease.key, lease.token, pair)
                    await run_in_threadpool(save_completion, database, lease.user_id, lease.session_id, lease.is_new, payload.message, state.get("document"), turn_id)
                except BaseException:
                    await store.restore(lease.key, lease.token, lease.snapshot)
                    raise
            return result
    except TimeoutError as exc:
        raise ModelUnavailableError() from exc


async def get_history(session_id: UUID, user_id: UUID, database: Database, store: SessionStore, settings: Settings, limit: int) -> HistoryData:
    lease = await prepare_chat(ChatRequest(message="读取历史", session_id=session_id), user_id=user_id, database=database, store=store, settings=settings)
    try:
        messages = parse_history(lease.snapshot)
        return HistoryData(session_id=session_id, messages=messages[-limit:], history_expired=not messages, warnings=[] if messages else [HISTORY_EXPIRED_WARNING])
    finally:
        await release_lease(store, lease)


async def delete_chat_session(database: Database, *, user_id: UUID, session_id: UUID, store: SessionStore, settings: Settings) -> None:
    lease = await prepare_chat(ChatRequest(message="删除咨询", session_id=session_id), user_id=user_id, database=database, store=store, settings=settings)
    try:
        with CancelScope(shield=True):
            try:
                await store.delete(lease.key, lease.token)
                await run_in_threadpool(delete_session, database, user_id, session_id)
            except BaseException:
                await store.restore(lease.key, lease.token, lease.snapshot)
                raise
    finally:
        await release_lease(store, lease)


async def get_conversations(user_id: UUID, database: Database, store: SessionStore, offset: int, limit: int) -> ConversationsData:
    rows, total = await run_in_threadpool(list_sessions, database, user_id, offset, limit)
    live = await store.exists_many([history_key(user_id, row.id) for row in rows])
    def utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return ConversationsData(items=[ConversationSummary(session_id=row.id, title=row.title, created_at=utc(row.created_at), updated_at=utc(row.updated_at), history_expired=not exists) for row, exists in zip(rows, live, strict=True)], total=total, offset=offset, limit=limit)
