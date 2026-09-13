"""Deterministic semantic section chunking for legal sources."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.enums import SourceType
from app.db.models import Case
from app.rag.normalization import canonical_hash, chunk_uuid, normalize_text

CHUNK_TARGET_MIN = 500
CHUNK_TARGET_MAX = 800
CHUNK_OVERLAP = 100


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    id: UUID
    source_type: SourceType
    source_id: UUID
    chunk_index: int
    section: str
    content: str
    content_hash: str
    character_count: int


def _split_long_text(text: str) -> list[str]:
    normalized = normalize_text(text)
    if len(normalized) <= CHUNK_TARGET_MAX:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        hard_end = min(start + CHUNK_TARGET_MAX, len(normalized))
        end = hard_end
        if hard_end < len(normalized):
            lower_bound = min(start + CHUNK_TARGET_MIN, hard_end)
            candidates = [
                normalized.rfind(mark, lower_bound, hard_end)
                for mark in ("。", "；", "！", "？", "\n")
            ]
            boundary = max(candidates)
            if boundary >= lower_bound:
                end = boundary + 1
        part = normalized[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(normalized):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def chunk_case(case: Case) -> list[ChunkDraft]:
    sections = (
        ("title", case.title),
        ("summary_facts", f"摘要：{case.summary}\n\n基本事实：{case.facts}"),
        ("dispute_focus", f"争议焦点：{case.dispute_focus}"),
        ("reasoning", f"演示分析：{case.reasoning}"),
    )
    drafts: list[ChunkDraft] = []
    chunk_index = 0
    for section, text in sections:
        for part_index, content in enumerate(_split_long_text(text)):
            content_hash = canonical_hash(
                {
                    "source_type": SourceType.CASE.value,
                    "source_id": str(case.id),
                    "section": section,
                    "part_index": part_index,
                    "content": content,
                }
            )
            drafts.append(
                ChunkDraft(
                    id=chunk_uuid(SourceType.CASE, case.id, section, part_index),
                    source_type=SourceType.CASE,
                    source_id=case.id,
                    chunk_index=chunk_index,
                    section=section,
                    content=content,
                    content_hash=content_hash,
                    character_count=len(content),
                )
            )
            chunk_index += 1
    return drafts
