"""Evaluate the frozen Week 2 queries with the pinned real BGE model."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import (
    BACKEND_DIR,
    EMBEDDING_QUERY_PREFIX,
    Settings,
)
from app.core.enums import LegalDomain
from app.db.session import Database
from app.rag.chunking import CHUNK_OVERLAP, CHUNK_TARGET_MAX, CHUNK_TARGET_MIN
from app.rag.embeddings import SentenceTransformerEmbedding, create_embedding_client
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.rag.retriever import (
    BM25_B,
    BM25_K1,
    PER_ROUTE_CANDIDATES,
    RRF_K,
    VECTOR_CHUNK_CANDIDATES,
    HybridCaseRetriever,
)
from app.rag.vector_store import ChromaVectorStore

DEFAULT_QUERIES = BACKEND_DIR / "data" / "evaluation" / "week2_queries.jsonl"
DEFAULT_CASES = BACKEND_DIR / "data" / "demo" / "cases.jsonl"


class EvaluationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query_id: str = Field(pattern=r"^W2-(MF|LD|TA|CD)-\d{3}$")
    domain: LegalDomain
    query: str = Field(min_length=1, max_length=1000)
    relevant_case_ids: list[str] = Field(min_length=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_queries(path: Path) -> list[EvaluationQuery]:
    records: list[EvaluationQuery] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(EvaluationQuery.model_validate_json(line))
        except ValidationError as exc:
            raise ValueError(f"Invalid evaluation query at line {line_number}") from exc
    if len(records) != 20:
        raise ValueError("The frozen evaluation set must contain exactly 20 queries")
    counts = Counter(record.domain for record in records)
    if counts != Counter({domain: 5 for domain in LegalDomain}):
        raise ValueError("The frozen evaluation set must contain five queries per domain")
    return records


def main() -> int:
    args = parse_args()
    queries_path = args.queries.resolve()
    cases_path = args.cases.resolve()
    settings = Settings()
    if settings.embedding_backend != "sentence_transformers":
        raise SystemExit("Real evaluation requires embedding_backend=sentence_transformers")

    queries = _load_queries(queries_path)
    database = Database(settings.database_url.get_secret_value())
    embedding = create_embedding_client(settings)
    if not isinstance(embedding, SentenceTransformerEmbedding):
        raise SystemExit("Pinned SentenceTransformer embedding is required")
    vector_store = ChromaVectorStore(
        settings.chroma_persist_directory,
        settings.chroma_collection_name,
        embedding,
    )
    try:
        import_summary = import_cases(database, load_case_records(cases_path))
        index_summary = index_cases(database, vector_store, embedding)
        if index_summary.failed:
            raise RuntimeError("At least one source failed real-model indexing")
        retriever = HybridCaseRetriever(database, vector_store, embedding)
        results = []
        hit_count = 0
        rankings_stable = True
        no_duplicate_cases = True
        for query in queries:
            first = retriever.search(
                query.query,
                domain=None,
                source_kind=None,
                top_k=5,
            )
            second = retriever.search(
                query.query,
                domain=None,
                source_kind=None,
                top_k=5,
            )
            ranking = [hit.case.case_number for hit in first]
            repeated_ranking = [hit.case.case_number for hit in second]
            rankings_stable = rankings_stable and ranking == repeated_ranking
            no_duplicate_cases = no_duplicate_cases and len(ranking) == len(set(ranking))
            matched = next(
                (case_id for case_id in ranking if case_id in query.relevant_case_ids),
                None,
            )
            hit = matched is not None
            hit_count += int(hit)
            results.append(
                {
                    "query_id": query.query_id,
                    "domain": query.domain.value,
                    "query": query.query,
                    "relevant_case_ids": query.relevant_case_ids,
                    "top_5": ranking,
                    "matched_case_id": matched,
                    "hit": hit,
                }
            )
    finally:
        database.dispose()

    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_dataset_sha256": _sha256(queries_path),
        "source_dataset_sha256": _sha256(cases_path),
        "configuration": {
            "embedding_model": embedding.model_name,
            "embedding_revision": embedding.model_revision,
            "embedding_dimension": embedding.dimension,
            "embedding_device": settings.embedding_device,
            "embedding_normalization": "l2",
            "query_prefix": EMBEDDING_QUERY_PREFIX,
            "query_prefix_version": embedding.query_prefix_version,
            "collection": settings.chroma_collection_name,
            "distance": "cosine",
            "chunk_target_min": CHUNK_TARGET_MIN,
            "chunk_target_max": CHUNK_TARGET_MAX,
            "chunk_overlap": CHUNK_OVERLAP,
            "bm25_k1": BM25_K1,
            "bm25_b": BM25_B,
            "vector_candidates": PER_ROUTE_CANDIDATES,
            "vector_internal_chunk_pool": VECTOR_CHUNK_CANDIDATES,
            "bm25_candidates": PER_ROUTE_CANDIDATES,
            "rrf_k": RRF_K,
        },
        "import": {
            "received": import_summary.received,
            "created": import_summary.created,
            "skipped": import_summary.skipped,
        },
        "index": {
            "received": index_summary.received,
            "indexed": index_summary.indexed,
            "failed": index_summary.failed,
            "chunks": index_summary.chunks,
            "persisted_vector_count": vector_store.count(),
        },
        "metrics": {
            "queries": len(queries),
            "top_5_hits": hit_count,
            "top_5_hit_rate": hit_count / len(queries),
            "minimum_hits": 16,
            "passed": hit_count >= 16,
            "rankings_stable": rankings_stable,
            "no_duplicate_cases": no_duplicate_cases,
        },
        "results": results,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["metrics"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
