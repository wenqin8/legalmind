"""Build the pinned, persistent Chroma index for pending legal data."""

from __future__ import annotations

import json
from dataclasses import asdict

from app.core.config import Settings
from app.db.session import Database
from app.rag.embeddings import create_embedding_client
from app.rag.indexer import index_cases
from app.rag.vector_store import ChromaVectorStore


def main() -> int:
    settings = Settings()
    database = Database(settings.database_url.get_secret_value())
    embedding = create_embedding_client(settings)
    vector_store = ChromaVectorStore(
        settings.chroma_persist_directory,
        settings.chroma_collection_name,
        embedding,
    )
    try:
        summary = index_cases(database, vector_store, embedding)
    finally:
        database.dispose()
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
