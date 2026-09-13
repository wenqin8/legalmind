"""Filtered vector/BM25 retrieval and equal-weight reciprocal rank fusion."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.enums import ImportStatus, LegalDomain, SourceKind, SourceType
from app.db.models import Case, KnowledgeChunk
from app.db.session import Database
from app.rag.bm25 import BM25Document, BM25Index
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import ChromaVectorStore

BM25_K1 = 1.5
BM25_B = 0.75
PER_ROUTE_CANDIDATES = 10
VECTOR_CHUNK_CANDIDATES = 40
RRF_K = 60


class RetrievalError(Exception):
    """A sanitized internal retrieval failure."""


@dataclass(frozen=True, slots=True)
class SearchHit:
    case: Case
    rrf_score: float
    vector_rank: int | None
    bm25_rank: int | None


def reciprocal_rank_fusion(
    vector_ids: list[UUID],
    bm25_ids: list[UUID],
    *,
    k: int = RRF_K,
) -> list[tuple[UUID, float, int | None, int | None]]:
    vector_ranks = {source_id: rank for rank, source_id in enumerate(vector_ids, 1)}
    bm25_ranks = {source_id: rank for rank, source_id in enumerate(bm25_ids, 1)}
    fused = []
    for source_id in set(vector_ranks) | set(bm25_ranks):
        vector_rank = vector_ranks.get(source_id)
        bm25_rank = bm25_ranks.get(source_id)
        score = (1 / (k + vector_rank) if vector_rank else 0.0) + (
            1 / (k + bm25_rank) if bm25_rank else 0.0
        )
        fused.append((source_id, score, vector_rank, bm25_rank))
    return sorted(
        fused,
        key=lambda item: (
            -item[1],
            item[2] if item[2] is not None else 10_000,
            item[3] if item[3] is not None else 10_000,
            str(item[0]),
        ),
    )


class HybridCaseRetriever:
    def __init__(
        self,
        database: Database,
        vector_store: ChromaVectorStore,
        embedding: EmbeddingClient,
    ) -> None:
        self.database = database
        self.vector_store = vector_store
        self.embedding = embedding

    @staticmethod
    def _case_filters(
        domain: LegalDomain | None,
        source_kind: SourceKind | None,
    ) -> list[object]:
        filters: list[object] = [Case.import_status == ImportStatus.INDEXED.value]
        if domain is not None:
            filters.append(Case.domain == domain.value)
        if source_kind is not None:
            filters.append(Case.source_kind == source_kind.value)
        return filters

    @staticmethod
    def _chroma_filter(
        domain: LegalDomain | None,
        source_kind: SourceKind | None,
    ) -> dict[str, object]:
        filters: list[dict[str, object]] = [{"source_type": SourceType.CASE.value}]
        if domain is not None:
            filters.append({"domain": domain.value})
        if source_kind is not None:
            filters.append({"source_kind": source_kind.value})
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def _bm25_ranked_sources(
        self,
        query: str,
        domain: LegalDomain | None,
        source_kind: SourceKind | None,
    ) -> list[UUID]:
        with self.database.session() as session:
            rows = session.execute(
                select(KnowledgeChunk, Case)
                .join(Case, Case.id == KnowledgeChunk.source_id)
                .where(*self._case_filters(domain, source_kind))
                .order_by(KnowledgeChunk.id)
            ).all()
        documents = [
            BM25Document(key=str(chunk.id), text=chunk.content) for chunk, _ in rows
        ]
        source_by_chunk = {str(chunk.id): case.id for chunk, case in rows}
        ranked_chunks = BM25Index(documents, k1=BM25_K1, b=BM25_B).search(
            query,
            limit=len(documents),
        )
        best_by_source: dict[UUID, float] = {}
        for chunk_id, score in ranked_chunks:
            source_id = source_by_chunk[chunk_id]
            best_by_source[source_id] = max(score, best_by_source.get(source_id, 0.0))
        return [
            source_id
            for source_id, _ in sorted(
                best_by_source.items(), key=lambda item: (-item[1], str(item[0]))
            )[:PER_ROUTE_CANDIDATES]
        ]

    def _vector_ranked_sources(
        self,
        query: str,
        domain: LegalDomain | None,
        source_kind: SourceKind | None,
    ) -> list[UUID]:
        vector = self.embedding.embed_query(query)
        result = self.vector_store.query(
            vector,
            n_results=VECTOR_CHUNK_CANDIDATES,
            where=self._chroma_filter(domain, source_kind),
        )
        ranked: list[UUID] = []
        for metadata in (result.get("metadatas") or [[]])[0]:
            try:
                source_id = UUID(str(metadata["source_id"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise RetrievalError("Vector index contains an invalid source reference") from exc
            if source_id not in ranked:
                ranked.append(source_id)
            if len(ranked) == PER_ROUTE_CANDIDATES:
                break
        return ranked

    def search(
        self,
        query: str,
        *,
        domain: LegalDomain | None,
        source_kind: SourceKind | None,
        top_k: int,
    ) -> list[SearchHit]:
        try:
            vector_ids = self._vector_ranked_sources(query, domain, source_kind)
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError("Retrieval backend is unavailable") from exc
        try:
            bm25_ids = self._bm25_ranked_sources(query, domain, source_kind)
        except SQLAlchemyError:
            raise

        fused = reciprocal_rank_fusion(vector_ids, bm25_ids)
        source_ids = [source_id for source_id, *_ in fused]
        if not source_ids:
            return []
        try:
            with self.database.session() as session:
                cases = list(
                    session.scalars(
                        select(Case).where(
                            Case.id.in_(source_ids),
                            *self._case_filters(domain, source_kind),
                        )
                    )
                )
        except SQLAlchemyError:
            raise
        cases_by_id = {case.id: case for case in cases}
        return [
            SearchHit(
                case=cases_by_id[source_id],
                rrf_score=score,
                vector_rank=vector_rank,
                bm25_rank=bm25_rank,
            )
            for source_id, score, vector_rank, bm25_rank in fused
            if source_id in cases_by_id
        ][:top_k]
