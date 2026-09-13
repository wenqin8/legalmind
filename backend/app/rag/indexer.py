"""Source-by-source indexing with explicit consistency states and cleanup."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.enums import ImportStatus
from app.db.models import Case, KnowledgeChunk
from app.db.session import Database
from app.rag.chunking import chunk_case
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import ChromaVectorStore


@dataclass(frozen=True, slots=True)
class IndexSummary:
    received: int
    indexed: int
    failed: int
    chunks: int


def _mark_failed(database: Database, case_id: object) -> None:
    try:
        with database.session() as session, session.begin():
            source = session.get(Case, case_id)
            if source is not None:
                session.execute(
                    delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id)
                )
                source.import_status = ImportStatus.FAILED
    except SQLAlchemyError:
        return


def index_cases(
    database: Database,
    vector_store: ChromaVectorStore,
    embedding: EmbeddingClient,
) -> IndexSummary:
    with database.session() as session:
        sources = list(
            session.scalars(
                select(Case)
                .where(
                    Case.import_status.in_(
                        [ImportStatus.PENDING.value, ImportStatus.FAILED.value]
                    )
                )
                .order_by(Case.case_number)
            )
        )

    indexed = 0
    failed = 0
    chunk_count = 0
    for source in sources:
        chunks = chunk_case(source)
        try:
            vectors = embedding.embed_documents([chunk.content for chunk in chunks])
            vector_store.delete_source(str(source.id))
            vector_store.upsert(
                chunks,
                vectors,
                {
                    "domain": str(source.domain),
                    "source_kind": str(source.source_kind),
                    "is_demo": source.is_demo,
                },
            )
            with database.session() as session, session.begin():
                current = session.get(Case, source.id)
                if current is None:
                    raise RuntimeError("Source disappeared while indexing")
                session.execute(
                    delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id)
                )
                session.add_all(
                    [
                        KnowledgeChunk(
                            id=chunk.id,
                            source_type=chunk.source_type,
                            source_id=chunk.source_id,
                            chunk_index=chunk.chunk_index,
                            section=chunk.section,
                            content=chunk.content,
                            content_hash=chunk.content_hash,
                            character_count=chunk.character_count,
                        )
                        for chunk in chunks
                    ]
                )
                current.import_status = ImportStatus.INDEXED
            indexed += 1
            chunk_count += len(chunks)
        except Exception:
            try:
                vector_store.delete_source(str(source.id))
            except Exception:
                pass
            _mark_failed(database, source.id)
            failed += 1

    return IndexSummary(
        received=len(sources),
        indexed=indexed,
        failed=failed,
        chunks=chunk_count,
    )
