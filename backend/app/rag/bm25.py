"""Dependency-free Okapi BM25 with deterministic Chinese tokenization."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

ASCII_TOKEN = re.compile(r"[a-z0-9]+")
CJK_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    lowered = text.casefold()
    tokens = [f"a:{match}" for match in ASCII_TOKEN.findall(lowered)]
    chinese = CJK_CHARACTER.findall(lowered)
    if len(chinese) == 1:
        tokens.append(f"c:{chinese[0]}")
    else:
        tokens.extend(
            f"c:{chinese[index]}{chinese[index + 1]}"
            for index in range(len(chinese) - 1)
        )
    return tokens


@dataclass(frozen=True, slots=True)
class BM25Document:
    key: str
    text: str


class BM25Index:
    def __init__(
        self,
        documents: Sequence[BM25Document],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self._tokens = [tokenize(document.text) for document in documents]
        self._frequencies = [Counter(tokens) for tokens in self._tokens]
        self._average_length = (
            sum(len(tokens) for tokens in self._tokens) / len(self._tokens)
            if self._tokens
            else 0.0
        )
        self._document_frequency = Counter(
            token for tokens in self._tokens for token in set(tokens)
        )

    def search(self, query: str, *, limit: int) -> list[tuple[str, float]]:
        if limit <= 0 or not self.documents:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        document_count = len(self.documents)
        scores: list[tuple[str, float]] = []
        for document, terms, frequencies in zip(
            self.documents,
            self._tokens,
            self._frequencies,
            strict=True,
        ):
            score = 0.0
            document_length = len(terms)
            for token in query_tokens:
                frequency = frequencies[token]
                if frequency == 0:
                    continue
                containing = self._document_frequency[token]
                inverse_document_frequency = math.log(
                    1 + (document_count - containing + 0.5) / (containing + 0.5)
                )
                length_ratio = (
                    document_length / self._average_length
                    if self._average_length
                    else 0.0
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length_ratio
                )
                score += inverse_document_frequency * (
                    frequency * (self.k1 + 1) / denominator
                )
            if score > 0:
                scores.append((document.key, score))
        return sorted(scores, key=lambda item: (-item[1], item[0]))[:limit]
