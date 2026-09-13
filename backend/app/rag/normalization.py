"""Deterministic text normalization, hashes, and identifiers for legal data."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid5

from app.core.enums import SourceType

LEGAL_DATA_NAMESPACE = UUID("3f0930d0-444f-5df3-9e19-5f8aa65b9c2a")
_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\r\n]+")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace without destroying paragraph boundaries."""

    normalized = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [_HORIZONTAL_WHITESPACE.sub(" ", line).strip() for line in normalized.split("\n")]
    return _EXCESS_NEWLINES.sub("\n\n", "\n".join(lines)).strip()


def canonical_hash(values: Mapping[str, Any]) -> str:
    payload = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_uuid(source_type: SourceType, stable_identifier: str) -> UUID:
    normalized_identifier = normalize_text(stable_identifier).casefold()
    return uuid5(LEGAL_DATA_NAMESPACE, f"{source_type.value}:{normalized_identifier}")


def chunk_uuid(source_type: SourceType, source_id: UUID, section: str, part_index: int) -> UUID:
    return uuid5(
        LEGAL_DATA_NAMESPACE,
        f"chunk:{source_type.value}:{source_id}:{section}:{part_index}",
    )
