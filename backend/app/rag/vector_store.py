"""Chroma adapter that never delegates embedding or source truth to Chroma."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import chromadb
from chromadb.errors import NotFoundError

from app.rag.chunking import ChunkDraft
from app.rag.embeddings import EmbeddingClient

INDEX_SCHEMA_VERSION = "legal-knowledge-v1"


class VectorStoreError(Exception):
    """Base error for sanitized retrieval/index failures."""


class IndexCompatibilityError(VectorStoreError):
    """An existing collection was built with incompatible settings."""


class ChromaVectorStore:
    def __init__(
        self,
        persist_directory: Path,
        collection_name: str,
        embedding: EmbeddingClient,
    ) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding = embedding
        self._client: Any | None = None
        self._collection: Any | None = None

    @property
    def expected_metadata(self) -> dict[str, str | int]:
        return {
            "index_schema_version": INDEX_SCHEMA_VERSION,
            "embedding_model": self.embedding.model_name,
            "embedding_revision": self.embedding.model_revision,
            "embedding_dimension": self.embedding.dimension,
            "embedding_normalization": "l2",
            "query_prefix_version": self.embedding.query_prefix_version,
        }

    def _open(self) -> Any:
        if self._collection is not None:
            return self._collection
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.persist_directory)
        try:
            collection = self._client.get_collection(
                self.collection_name,
                embedding_function=None,
            )
        except NotFoundError:
            collection = self._client.create_collection(
                self.collection_name,
                configuration={"hnsw": {"space": "cosine"}},
                metadata=self.expected_metadata,
                embedding_function=None,
            )
        if collection.metadata != self.expected_metadata:
            raise IndexCompatibilityError(
                "Chroma collection embedding metadata is incompatible"
            )
        if collection.configuration.get("hnsw", {}).get("space") != "cosine":
            raise IndexCompatibilityError("Chroma collection must use cosine space")
        self._collection = collection
        return collection

    @staticmethod
    def _validate_vectors(vectors: Sequence[Sequence[float]], dimension: int) -> None:
        if any(len(vector) != dimension for vector in vectors):
            raise IndexCompatibilityError("Embedding vector dimension is incompatible")

    def upsert(
        self,
        chunks: Sequence[ChunkDraft],
        vectors: Sequence[Sequence[float]],
        metadata: Mapping[str, str | bool],
    ) -> None:
        if len(chunks) != len(vectors):
            raise VectorStoreError("Chunk and embedding counts differ")
        self._validate_vectors(vectors, self.embedding.dimension)
        collection = self._open()
        metadatas = [
            {
                **metadata,
                "source_type": chunk.source_type.value,
                "source_id": str(chunk.source_id),
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "content_hash": chunk.content_hash,
            }
            for chunk in chunks
        ]
        collection.upsert(
            ids=[str(chunk.id) for chunk in chunks],
            embeddings=[list(vector) for vector in vectors],
            documents=[chunk.content for chunk in chunks],
            metadatas=metadatas,
        )

    def query(
        self,
        vector: Sequence[float],
        *,
        n_results: int,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_vectors([vector], self.embedding.dimension)
        if n_results <= 0:
            raise ValueError("n_results must be positive")
        return self._open().query(
            query_embeddings=[list(vector)],
            n_results=n_results,
            where=dict(where) if where else None,
            include=["metadatas", "distances", "documents"],
        )

    def delete_ids(self, ids: Sequence[str]) -> None:
        if ids:
            self._open().delete(ids=list(ids))

    def delete_source(self, source_id: str) -> None:
        self._open().delete(where={"source_id": source_id})

    def count(self) -> int:
        return int(self._open().count())
