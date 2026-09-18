"""Authenticated graph execution, SSE and owned short-term history."""

import json
import logging
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import AuthenticatedUser, get_current_user, get_database, get_llm_client, get_runtime_settings, get_case_retriever, get_session_store
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever
from app.schemas.chat import ChatData, ChatRequest, DeletedConversationData, HistoryData, ConversationsData
from app.schemas.common import ApiSuccess
from app.services.chat import prepare_chat, execute_chat, release_lease, delete_chat_session, get_history, get_conversations
from app.services.session_store import SessionStore

router = APIRouter(prefix="/chat")
logger = logging.getLogger("app.chat.stream")


@dataclass
class ChatRuntime:
    user: AuthenticatedUser
    database: Database
    llm: LLMClient
    settings: Settings
    retriever: HybridCaseRetriever
    store: SessionStore


def runtime(user: Annotated[AuthenticatedUser, Depends(get_current_user)],
            database: Annotated[Database, Depends(get_database)],
            llm: Annotated[LLMClient, Depends(get_llm_client)],
            settings: Annotated[Settings, Depends(get_runtime_settings)],
            retriever: Annotated[HybridCaseRetriever, Depends(get_case_retriever)],
            store: Annotated[SessionStore, Depends(get_session_store)]) -> ChatRuntime:
    return ChatRuntime(user, database, llm, settings, retriever, store)


Runtime = Annotated[ChatRuntime, Depends(runtime)]


@router.post("/send", response_model=ApiSuccess[ChatData])
async def send_chat_message(payload: ChatRequest, request: Request, context: Runtime):
    lease = await prepare_chat(payload, user_id=context.user.id, database=context.database, store=context.store, settings=context.settings)
    try:
        data = await execute_chat(payload, lease, request_id=request.state.request_id, database=context.database,
                                  store=context.store, settings=context.settings, llm=context.llm, retriever=context.retriever)
        return ApiSuccess(data=data, request_id=request.state.request_id)
    finally:
        await release_lease(context.store, lease)


def encode_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


@router.post("/stream")
async def stream_chat(payload: ChatRequest, request: Request, context: Runtime):
    # Ownership and Redis availability are checked before HTTP response headers.
    lease = await prepare_chat(payload, user_id=context.user.id, database=context.database, store=context.store, settings=context.settings)

    async def events():
        sender, receiver = anyio.create_memory_object_stream(16)

        async def emit(event: str, data: dict):
            await sender.send((event, data))

        async def produce():
            async with sender:
                try:
                    result = await execute_chat(payload, lease, request_id=request.state.request_id, database=context.database,
                                                store=context.store, settings=context.settings, llm=context.llm,
                                                retriever=context.retriever, emit=emit)
                    await emit("sources", {"items": [source.model_dump(mode="json") for source in result.sources]})
                    await emit("done", {"success": True, "warnings": result.warnings, "missing_fields": result.missing_fields,
                                        "document_id": str(result.document_id) if result.document_id else None,
                                        "task": result.task.model_dump(mode="json") if result.task else None})
                except AppError as exc:
                    await emit("error", {"code": exc.code, "message": exc.message, "request_id": str(request.state.request_id)})
                    await emit("done", {"success": False})
                except Exception as exc:
                    logger.error("stream_failed", extra={"event": "stream_failed", "exception_type": type(exc).__name__})
                    await emit("error", {"code": "INTERNAL_ERROR", "message": "服务暂时不可用，请稍后重试", "request_id": str(request.state.request_id)})
                    await emit("done", {"success": False})

        async with receiver, anyio.create_task_group() as group:
            group.start_soon(produce)
            try:
                async for event, data in receiver:
                    yield encode_event(event, data)
            finally:
                group.cancel_scope.cancel()

    class OwnedStream(StreamingResponse):
        async def __call__(self, scope, receive, send):
            try:
                await super().__call__(scope, receive, send)
            finally:
                await release_lease(context.store, lease)

    return OwnedStream(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/conversations", response_model=ApiSuccess[ConversationsData])
async def conversations(request: Request, context: Runtime, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    data = await get_conversations(context.user.id, context.database, context.store, offset, limit)
    return ApiSuccess(data=data, request_id=request.state.request_id)


@router.get("/history/{session_id}", response_model=ApiSuccess[HistoryData])
async def history(session_id: UUID, request: Request, context: Runtime, limit: int = Query(20, ge=1, le=50)):
    data = await get_history(session_id, context.user.id, context.database, context.store, context.settings, limit)
    return ApiSuccess(data=data, request_id=request.state.request_id)


@router.delete("/history/{session_id}", response_model=ApiSuccess[DeletedConversationData])
async def delete_conversation(session_id: UUID, request: Request, context: Runtime):
    await delete_chat_session(context.database, user_id=context.user.id, session_id=session_id, store=context.store, settings=context.settings)
    return ApiSuccess(data=DeletedConversationData(deleted_session_id=session_id), request_id=request.state.request_id)
