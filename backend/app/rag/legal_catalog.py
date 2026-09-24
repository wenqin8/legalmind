"""Reviewed local statute versions; deliberately independent of the frozen case index."""

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.rag.bm25 import BM25Document, BM25Index

from app.core.errors import RetrievalUnavailableError
from app.db.models import LegalProvision
from app.db.session import Database
from app.rag.importer import normalize_legal_provision
from app.rag.schemas import LegalProvisionSourceRecord
from app.schemas.tasks import Domain


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_until: date | None = None  # exclusive
    verified_at: date
    status_as_of: date
    status_source_url: str
    original_text: str = Field(min_length=1, max_length=30000)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    domains: list[Domain] = Field(min_length=1, max_length=4)
    keywords: list[str] = Field(min_length=1, max_length=30)
    temporal_rule: Literal['event_date', 'pending_after_effective'] = 'event_date'
    transition_text: str | None = None

    @model_validator(mode="after")
    def validate_version(self):
        if hashlib.sha256(self.original_text.encode("utf-8")).hexdigest() != self.text_sha256:
            raise ValueError("Verbatim text hash mismatch")
        if self.status_as_of > self.verified_at or self.verified_at > date.today():
            raise ValueError("Invalid verification date")
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("Empty effective interval")
        require_official_url(self.status_source_url)
        return self


def require_official_url(value: str):
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or parsed.username or parsed.password or not host.endswith(".gov.cn"):
        raise ValueError("An official HTTPS source is required")


class CatalogRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: LegalProvisionSourceRecord
    verification: Verification

    @model_validator(mode="after")
    def match_record(self):
        require_official_url(str(self.record.source_url))
        if self.record.source_kind.value != "official" or self.record.content != self.verification.original_text:
            raise ValueError("Record must preserve reviewed official text")
        if self.record.effective_at != self.verification.effective_from:
            raise ValueError("Effective dates disagree")
        return self


def load_catalog(path: Path) -> list[CatalogRecord]:
    records = [CatalogRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records or len({r.record.record_id for r in records}) != len(records):
        raise ValueError("Empty or duplicate catalog")
    return records


def import_catalog(database: Database, records: list[CatalogRecord]) -> dict[str, int]:
    """A manual, transactional update; never replace an existing version's text."""
    created = updated = 0
    with database.session() as session, session.begin():
        for entry in records:
            entry = CatalogRecord.model_validate(entry.model_dump())
            record = normalize_legal_provision(entry.record)
            existing = session.scalar(select(LegalProvision).where(LegalProvision.record_id == record.record_id))
            metadata = entry.verification.model_dump(mode="json")
            if existing:
                if existing.content_hash != record.content_hash:
                    raise ValueError("Version content changed: use a new version identifier")
                if existing.verification and existing.verification["verified_at"] > metadata["verified_at"]:
                    raise ValueError("Cannot roll back verification date")
                existing.verification = metadata
                existing.legal_status = entry.record.legal_status.value
                updated += 1
            else:
                session.add(LegalProvision(**record.model_dump(mode="python"), verification=metadata))
                created += 1
        session.flush()
        intervals: dict[tuple[str, str], list[Verification]] = {}
        for row in session.scalars(select(LegalProvision).where(LegalProvision.verification.is_not(None))):
            metadata = Verification.model_validate(row.verification)
            key = (row.regulation_name, row.article_number)
            for old in intervals.get(key, []):
                if max(old.effective_from, metadata.effective_from) < min(old.effective_until or date.max, metadata.effective_until or date.max):
                    raise ValueError("Overlapping versions: close the older interval in the same import")
            intervals.setdefault(key, []).append(metadata)
    return {"created": created, "updated": updated}


def event_interval(value: str) -> tuple[date, date] | None:
    # Relative or invalid dates are never silently interpreted as today.
    matches = list(re.finditer(r"(?<!\d)(\d{4})(?:年|[-/])(?:(\d{1,2})(?:月|[-/])?(?:(\d{1,2})日?)?)?", value))
    if not matches:
        return None
    bounds = []
    from calendar import monthrange
    try:
        for m in matches:
            year, month, day = int(m[1]), int(m[2]) if m[2] else None, int(m[3]) if m[3] else None
            bounds.extend([date(year, month or 1, day or 1), date(year, month or 12, day or (monthrange(year, month)[1] if month else 31))])
    except ValueError:
        return None
    return min(bounds), max(bounds)


def tokens(value: str) -> list[str]:
    text = re.sub(r"\s+", "", value.lower())
    return [text[i:i+2] for i in range(len(text)-1)]


def uncertain_case_status(value: str | None) -> bool:
    return bool(value and re.search(r'是否|不(?:清楚|知道|确定|是)|可能|也许|或许|记不清|[?？]', value))


def pending_case(value: str | None) -> bool:
    return bool(value and re.search(r'尚未终审|未终审|没有生效裁判|未有生效裁判', value)
                and not re.search(r'已经终审|已终审|再审', value) and not uncertain_case_status(value))


def retrieve_provisions(database: Database, query: str, domain: Domain | None, *, event_date: str | None,
                        general: bool = False, case_status: str | None = None,
                        include_transition_questions: bool = False) -> list[tuple[LegalProvision, Verification]]:
    interval = event_interval(event_date or "")
    if not general and interval is None:
        return []
    try:
        with database.session() as session:
            rows = session.scalars(select(LegalProvision).where(LegalProvision.verification.is_not(None))).all()
        candidates = []
        for row in rows:
            metadata = Verification.model_validate(row.verification)
            if domain is not None and domain not in metadata.domains:
                continue
            if row.legal_status == "unknown" or (row.legal_status in {"amended", "repealed"} and metadata.effective_until is None):
                continue
            if general:
                if row.legal_status != "effective" or metadata.effective_from > date.today() or (metadata.effective_until and metadata.effective_until <= date.today()):
                    continue
            else:
                pending_rule = metadata.temporal_rule == 'pending_after_effective' and metadata.effective_from <= date.today()
                status_missing = not case_status or uncertain_case_status(case_status)
                if pending_rule and not status_missing and not pending_case(case_status) and metadata.effective_from > interval[0]:
                    continue
                if metadata.effective_from > interval[0] and not (pending_rule and (pending_case(case_status) or (include_transition_questions and status_missing))):
                    continue
                if metadata.effective_until and metadata.effective_until <= interval[1]:
                    continue
            candidates.append((row, metadata))
        if not candidates:
            return []
        corpus = [BM25Document(row.record_id, " ".join(m.keywords) + " " + m.original_text) for row, m in candidates]
        lookup = {row.record_id: (row, m) for row, m in candidates}
        ranked = [(lookup[key], score) for key, score in BM25Index(corpus).search(query, limit=len(corpus))]
        # Keywords contribute to ranking, but lexical synonyms must not delete top hits.
        # Candidate scores do not authorize an answer: direct support is checked downstream.
        return [pair for pair, score in ranked if score > 0][:5]
    except (SQLAlchemyError, ValueError, TypeError) as exc:
        raise RetrievalUnavailableError() from exc
