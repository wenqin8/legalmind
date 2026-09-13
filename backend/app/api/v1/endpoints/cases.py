"""Authenticated case retrieval endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import (
    AuthenticatedUser,
    get_case_retriever,
    get_current_user,
    get_database,
)
from app.db.session import Database
from app.rag.retriever import HybridCaseRetriever
from app.schemas.cases import CaseDetailData, CaseSearchData, CaseSearchRequest
from app.schemas.common import ApiSuccess
from app.services.cases import get_case_detail, search_cases

router = APIRouter(prefix="/cases")


@router.post("/search", response_model=ApiSuccess[CaseSearchData])
def search_case_records(
    payload: CaseSearchRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    retriever: Annotated[HybridCaseRetriever, Depends(get_case_retriever)],
) -> ApiSuccess[CaseSearchData]:
    request.state.user_id = current_user.id
    return ApiSuccess(
        data=search_cases(payload, retriever),
        request_id=request.state.request_id,
    )


@router.get("/{case_id}", response_model=ApiSuccess[CaseDetailData])
def get_case_record(
    case_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> ApiSuccess[CaseDetailData]:
    request.state.user_id = current_user.id
    return ApiSuccess(
        data=get_case_detail(case_id, database),
        request_id=request.state.request_id,
    )
