"""Authenticated synchronous chat endpoint."""

from typing import Annotated

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
from app.schemas.chat import ChatData, ChatRequest
from app.schemas.common import ApiSuccess
from app.services.chat import answer_chat

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
