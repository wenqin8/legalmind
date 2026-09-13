"""Case search and detail use cases with source-of-truth database reads."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.enums import ImportStatus
from app.core.errors import (
    DatabaseUnavailableError,
    ResourceNotFoundError,
    RetrievalUnavailableError,
)
from app.db.models import Case
from app.db.session import Database
from app.rag.retriever import HybridCaseRetriever, RetrievalError
from app.schemas.cases import (
    DEMO_CASE_WARNING,
    CaseDetailData,
    CaseSearchData,
    CaseSearchItem,
    CaseSearchRequest,
)


def search_cases(
    payload: CaseSearchRequest,
    retriever: HybridCaseRetriever,
) -> CaseSearchData:
    try:
        hits = retriever.search(
            payload.query,
            domain=payload.domain,
            source_kind=payload.source_kind,
            top_k=payload.top_k,
        )
    except RetrievalError as exc:
        raise RetrievalUnavailableError() from exc
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc

    items = [
        CaseSearchItem(
            id=hit.case.id,
            title=hit.case.title,
            case_number=hit.case.case_number,
            court=hit.case.court,
            judgment_date=hit.case.judgment_date,
            source_url=hit.case.source_url,
            domain=hit.case.domain,
            summary=hit.case.summary,
            source_kind=hit.case.source_kind,
            is_demo=hit.case.is_demo,
            is_synthetic=hit.case.is_synthetic,
            rrf_score=hit.rrf_score,
            vector_rank=hit.vector_rank,
            bm25_rank=hit.bm25_rank,
        )
        for hit in hits
    ]
    return CaseSearchData(items=items, count=len(items))


def get_case_detail(case_id: UUID, database: Database) -> CaseDetailData:
    try:
        with database.session() as session:
            case = session.scalar(
                select(Case).where(
                    Case.id == case_id,
                    Case.import_status == ImportStatus.INDEXED.value,
                )
            )
            if case is None:
                raise ResourceNotFoundError()
            return CaseDetailData(
                id=case.id,
                title=case.title,
                case_number=case.case_number,
                court=case.court,
                judgment_date=case.judgment_date,
                sample_date=case.sample_date,
                domain=case.domain,
                summary=case.summary,
                facts=case.facts,
                dispute_focus=case.dispute_focus,
                reasoning=case.reasoning,
                law_references=case.law_references,
                source_kind=case.source_kind,
                source_url=case.source_url,
                source_title=case.source_title,
                publisher=case.publisher,
                source_description=case.source_description,
                authorization_note=case.authorization_note,
                is_demo=case.is_demo,
                is_synthetic=case.is_synthetic,
                warning=DEMO_CASE_WARNING if case.is_demo else "",
            )
    except ResourceNotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc
