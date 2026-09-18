"""Owned document templates, generation and fixed-format downloads."""

from typing import Annotated, Literal
from uuid import UUID

from anyio import fail_after
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.api.dependencies import AuthenticatedUser, get_current_user, get_database, get_case_retriever, get_llm_client, get_runtime_settings
from app.core.config import Settings
from app.core.errors import ModelUnavailableError
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever
from app.schemas.common import ApiSuccess
from app.schemas.documents import DocumentData, DocumentRequest, TemplatesData, TEMPLATES
from app.services.documents import prepare_document, save_document, read_document, plain_text

router = APIRouter(prefix="/documents")


@router.get("/templates", response_model=ApiSuccess[TemplatesData])
async def templates(request: Request, user: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return ApiSuccess(data=TemplatesData(items=list(TEMPLATES.values())), request_id=request.state.request_id)


@router.post("/generate", response_model=ApiSuccess[DocumentData])
async def generate(payload: DocumentRequest, request: Request,
                   user: Annotated[AuthenticatedUser, Depends(get_current_user)],
                   database: Annotated[Database, Depends(get_database)],
                   retriever: Annotated[HybridCaseRetriever, Depends(get_case_retriever)],
                   llm: Annotated[LLMClient, Depends(get_llm_client)],
                   settings: Annotated[Settings, Depends(get_runtime_settings)]):
    try:
        with fail_after(settings.deepseek_timeout_seconds + 5):
            prepared = await prepare_document(payload, database, retriever, llm)
            await run_in_threadpool(save_document, prepared, user.id, database)
    except TimeoutError as exc:
        raise ModelUnavailableError() from exc
    return ApiSuccess(data=prepared.data, request_id=request.state.request_id)


@router.get("/{document_id}/download")
async def download(document_id: UUID, user: Annotated[AuthenticatedUser, Depends(get_current_user)],
                   database: Annotated[Database, Depends(get_database)], format: Literal["md", "txt"] = "md"):
    document = await run_in_threadpool(read_document, document_id, user.id, database)
    body = document.content if format == "md" else plain_text(document.content)
    return Response(content=body, media_type="text/markdown" if format == "md" else "text/plain",
                    headers={"Content-Disposition": f'attachment; filename="{document.document_type}-{document.id}.{format}"', "Cache-Control": "no-store"})
