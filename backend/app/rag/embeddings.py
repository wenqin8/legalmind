"""Injectable embedding clients with a fixed, inspectable index identity."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.core.config import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_MODEL_REVISION,
    EMBEDDING_QUERY_PREFIX,
    EMBEDDING_QUERY_PREFIX_VERSION,
    Settings,
)


class EmbeddingClient(Protocol):
    model_name: str
    model_revision: str
    dimension: int
    query_prefix_version: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class DeterministicHashEmbedding:
    """Offline Chinese character n-gram feature hashing for automated tests."""

    model_name = "test/chinese-ngram-hash-v1"
    model_revision = "1"
    query_prefix_version = EMBEDDING_QUERY_PREFIX_VERSION

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        if dimension <= 0:
            raise ValueError("Embedding dimension must be positive")
        self.dimension = dimension

    @staticmethod
    def _tokens(text: str) -> list[str]:
        compact = "".join(text.casefold().split())
        if len(compact) < 2:
            return list(compact)
        return [compact[index : index + 2] for index in range(len(compact) - 1)]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in self._tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        return _l2_normalize(vector)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class SentenceTransformerEmbedding:
    """Lazy CPU adapter for the pinned BGE model."""

    model_name = EMBEDDING_MODEL_NAME
    model_revision = EMBEDDING_MODEL_REVISION
    dimension = EMBEDDING_DIMENSION
    query_prefix_version = EMBEDDING_QUERY_PREFIX_VERSION

    def __init__(self, cache_directory: Path, *, device: str = "cpu") -> None:
        self._cache_directory = cache_directory
        self._device = device
        self._model: object | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _load(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._cache_directory.mkdir(parents=True, exist_ok=True)
            self._model = SentenceTransformer(
                self.model_name,
                revision=self.model_revision,
                device=self._device,
                cache_folder=str(self._cache_directory),
            )
        return self._model

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        encoded = model.encode(  # type: ignore[attr-defined]
            list(texts),
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        vectors = encoded.tolist()
        if any(len(vector) != self.dimension for vector in vectors):
            raise ValueError("Embedding model returned an incompatible dimension")
        return vectors

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([EMBEDDING_QUERY_PREFIX + text])[0]


def create_embedding_client(settings: Settings) -> EmbeddingClient:
    if settings.embedding_backend == "fake":
        return DeterministicHashEmbedding(settings.embedding_dimension)
    return SentenceTransformerEmbedding(
        settings.embedding_cache_directory,
        device=settings.embedding_device,
    )
