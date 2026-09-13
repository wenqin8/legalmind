"""Authenticated synchronous chat endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_database,
    get_llm_client,
    get_runtime_settings,
)
from app.core.config import Settings
from app.db.session import Database
from app.llm.base import LLMClient
from app.schemas.chat import ChatData, ChatRequest, DeletedConversationData
from app.schemas.common import ApiSuccess
from app.services.chat import answer_chat, delete_chat_session

router = APIRouter(prefix="/chat")


@router.post("/send", response_model=ApiSuccess[ChatData])
async def send_chat_message(
    payload: ChatRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> ApiSuccess[ChatData]:
    """Generate one response without RAG or message-body persistence."""

    request.state.user_id = current_user.id
    data = await answer_chat(
        payload,
        current_user=current_user,
        llm_client=llm_client,
        database=database,
        settings=settings,
    )
    return ApiSuccess(data=data, request_id=request.state.request_id)


@router.delete("/history/{session_id}", response_model=ApiSuccess[DeletedConversationData])
async def delete_conversation(
    session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> ApiSuccess[DeletedConversationData]:
    """Delete an owned conversation without revealing other users' session IDs."""

    request.state.user_id = current_user.id
    await delete_chat_session(
        database,
        user_id=current_user.id,
        session_id=session_id,
    )
    return ApiSuccess(
        data=DeletedConversationData(deleted_session_id=session_id),
        request_id=request.state.request_id,
    )
