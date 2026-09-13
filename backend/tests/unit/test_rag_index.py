from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.enums import ImportStatus
from app.db.base import Base
from app.db.models import Case, KnowledgeChunk
from app.db.session import Database
from app.rag.chunking import CHUNK_TARGET_MAX, chunk_case
from app.rag.embeddings import DeterministicHashEmbedding, SentenceTransformerEmbedding
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.rag.vector_store import ChromaVectorStore, IndexCompatibilityError

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.jsonl"


@pytest.fixture
def imported_database(tmp_path: Path):
    database = Database(f"sqlite:///{(tmp_path / 'index.db').as_posix()}")
    Base.metadata.create_all(database.engine)
    import_cases(database, load_case_records(DATASET_PATH))
    try:
        yield database
    finally:
        database.dispose()


def _first_case(database: Database) -> Case:
    with database.session() as session:
        source = session.scalar(select(Case).order_by(Case.case_number))
        assert source is not None
        return source


def test_case_chunking_is_semantic_and_deterministic(
    imported_database: Database,
) -> None:
    source = _first_case(imported_database)
    first = chunk_case(source)
    second = chunk_case(source)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.content_hash for chunk in first] == [
        chunk.content_hash for chunk in second
    ]
    assert [chunk.section for chunk in first] == [
        "title",
        "summary_facts",
        "dispute_focus",
        "reasoning",
    ]
    assert all(chunk.character_count == len(chunk.content) for chunk in first)


def test_long_sections_respect_maximum_and_overlap(
    imported_database: Database,
) -> None:
    source = _first_case(imported_database)
    source.facts = "甲方持续履行约定义务。" * 180

    fact_chunks = [
        chunk for chunk in chunk_case(source) if chunk.section == "summary_facts"
    ]

    assert len(fact_chunks) > 1
    assert all(len(chunk.content) <= CHUNK_TARGET_MAX for chunk in fact_chunks)
    assert fact_chunks[0].content[-50:] in fact_chunks[1].content


def test_fake_embedding_is_deterministic_normalized_and_512_dimensional() -> None:
    embedding = DeterministicHashEmbedding()
    first = embedding.embed_query("拖欠工资")
    second = embedding.embed_query("拖欠工资")

    assert first == second
    assert len(first) == 512
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_sentence_transformer_adapter_stays_lazy(tmp_path: Path) -> None:
    embedding = SentenceTransformerEmbedding(tmp_path / "models")

    assert embedding.is_loaded is False
    assert not (tmp_path / "models").exists()


def test_chroma_persists_source_references_and_rejects_mismatch(
    imported_database: Database,
    tmp_path: Path,
) -> None:
    source = _first_case(imported_database)
    chunks = chunk_case(source)
    embedding = DeterministicHashEmbedding()
    vectors = embedding.embed_documents([chunk.content for chunk in chunks])
    path = tmp_path / "chroma"
    first = ChromaVectorStore(path, "legal_knowledge_v1", embedding)
    first.upsert(
        chunks,
        vectors,
        {"domain": source.domain, "source_kind": source.source_kind, "is_demo": True},
    )

    reopened = ChromaVectorStore(path, "legal_knowledge_v1", embedding)
    result = reopened.query(embedding.embed_query(source.title), n_results=4)

    assert reopened.count() == len(chunks)
    assert str(source.id) in {
        metadata["source_id"] for metadata in result["metadatas"][0]
    }
    incompatible = ChromaVectorStore(
        path,
        "legal_knowledge_v1",
        DeterministicHashEmbedding(dimension=64),
    )
    with pytest.raises(IndexCompatibilityError, match="metadata"):
        incompatible.count()


def test_indexer_commits_database_chunks_only_after_vectors(
    imported_database: Database,
    tmp_path: Path,
) -> None:
    embedding = DeterministicHashEmbedding()
    store = ChromaVectorStore(tmp_path / "index", "legal_knowledge_v1", embedding)

    summary = index_cases(imported_database, store, embedding)

    assert summary.received == 16
    assert summary.indexed == 16
    assert summary.failed == 0
    assert summary.chunks == 64
    assert store.count() == 64
    with imported_database.session() as session:
        assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 64
        assert session.scalar(
            select(func.count()).where(Case.import_status == ImportStatus.INDEXED)
        ) == 16


def test_index_failure_cleans_vectors_chunks_and_marks_failed(
    imported_database: Database,
    tmp_path: Path,
) -> None:
    class FailingEmbedding(DeterministicHashEmbedding):
        def embed_documents(self, texts):  # type: ignore[no-untyped-def]
            raise RuntimeError("private provider error")

    with imported_database.session() as session, session.begin():
        for source in session.scalars(select(Case).order_by(Case.case_number).offset(1)):
            source.import_status = ImportStatus.INDEXED

    embedding = FailingEmbedding()
    store = ChromaVectorStore(tmp_path / "failed", "legal_knowledge_v1", embedding)
    summary = index_cases(imported_database, store, embedding)

    assert summary.failed == 1
    with imported_database.session() as session:
        failed_case = session.scalar(
            select(Case).where(Case.import_status == ImportStatus.FAILED)
        )
        assert failed_case is not None
        assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0


def test_partial_vector_write_is_removed_by_source(
    imported_database: Database,
    tmp_path: Path,
) -> None:
    class PartialFailureStore(ChromaVectorStore):
        def upsert(self, chunks, vectors, metadata):  # type: ignore[no-untyped-def]
            super().upsert(chunks, vectors, metadata)
            raise RuntimeError("failure after vector write")

    with imported_database.session() as session, session.begin():
        for source in session.scalars(select(Case).order_by(Case.case_number).offset(1)):
            source.import_status = ImportStatus.INDEXED

    embedding = DeterministicHashEmbedding()
    store = PartialFailureStore(tmp_path / "partial", "legal_knowledge_v1", embedding)
    summary = index_cases(imported_database, store, embedding)

    assert summary.failed == 1
    assert store.count() == 0
    with imported_database.session() as session:
        assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0
