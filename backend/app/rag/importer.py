"""Validated, transactional, and repeatable legal-data imports."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.enums import ImportStatus, SourceType
from app.db.models import Case, LegalProvision
from app.db.session import Database
from app.rag.normalization import canonical_hash, normalize_text, source_uuid
from app.rag.schemas import (
    CaseSourceRecord,
    ImportSummary,
    LegalProvisionSourceRecord,
    NormalizedCaseRecord,
    NormalizedLegalProvisionRecord,
)


class DataImportError(Exception):
    """A safe import failure without including source payloads."""


class ImportConflictError(DataImportError):
    """A stable identifier or content hash conflicts with stored data."""


RecordT = TypeVar("RecordT", bound=BaseModel)


def _load_jsonl_records(
    path: Path,
    schema: type[RecordT],
    *,
    label: str,
) -> list[RecordT]:
    records: list[RecordT] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            records.append(schema.model_validate(payload))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise DataImportError(f"Invalid {label} record at line {line_number}") from exc
    if not records:
        raise DataImportError(f"{label.capitalize()} dataset is empty")
    return records


def load_case_records(path: Path) -> list[CaseSourceRecord]:
    return _load_jsonl_records(path, CaseSourceRecord, label="case")


def load_legal_provision_records(path: Path) -> list[LegalProvisionSourceRecord]:
    return _load_jsonl_records(path, LegalProvisionSourceRecord, label="legal-provision")


def normalize_case(record: CaseSourceRecord) -> NormalizedCaseRecord:
    normalized_text = {
        "case_number": normalize_text(record.case_number),
        "title": normalize_text(record.title),
        "summary": normalize_text(record.summary),
        "facts": normalize_text(record.facts),
        "dispute_focus": normalize_text(record.dispute_focus),
        "reasoning": normalize_text(record.reasoning),
        "source_title": normalize_text(record.source_title),
        "source_description": normalize_text(record.source_description),
        "authorization_note": normalize_text(record.authorization_note),
    }
    normalized_references = [normalize_text(value) for value in record.law_references]
    content_hash = canonical_hash(
        {
            "title": normalized_text["title"],
            "domain": record.domain.value,
            "summary": normalized_text["summary"],
            "facts": normalized_text["facts"],
            "dispute_focus": normalized_text["dispute_focus"],
            "reasoning": normalized_text["reasoning"],
            "law_references": normalized_references,
        }
    )
    return NormalizedCaseRecord(
        id=source_uuid(SourceType.CASE, normalized_text["case_number"]),
        case_number=normalized_text["case_number"],
        title=normalized_text["title"],
        domain=record.domain,
        summary=normalized_text["summary"],
        facts=normalized_text["facts"],
        dispute_focus=normalized_text["dispute_focus"],
        reasoning=normalized_text["reasoning"],
        court=normalize_text(record.court) if record.court else None,
        judgment_date=record.judgment_date,
        sample_date=record.sample_date,
        law_references=normalized_references,
        source_kind=record.source_kind,
        source_title=normalized_text["source_title"],
        source_description=normalized_text["source_description"],
        source_url=str(record.source_url) if record.source_url else None,
        publisher=normalize_text(record.publisher) if record.publisher else None,
        is_demo=record.is_demo,
        is_synthetic=record.is_synthetic,
        collected_at=record.collected_at,
        authorization_note=normalized_text["authorization_note"],
        content_hash=content_hash,
    )


def normalize_legal_provision(
    record: LegalProvisionSourceRecord,
) -> NormalizedLegalProvisionRecord:
    normalized_text = {
        "record_id": normalize_text(record.record_id),
        "regulation_name": normalize_text(record.regulation_name),
        "article_number": normalize_text(record.article_number),
        "content": normalize_text(record.content),
        "issuing_authority": normalize_text(record.issuing_authority),
        "source_title": normalize_text(record.source_title),
        "source_description": normalize_text(record.source_description),
        "publisher": normalize_text(record.publisher or ""),
        "authorization_note": normalize_text(record.authorization_note),
    }
    content_hash = canonical_hash(
        {
            "regulation_name": normalized_text["regulation_name"],
            "article_number": normalized_text["article_number"],
            "content": normalized_text["content"],
            "issuing_authority": normalized_text["issuing_authority"],
            "published_at": record.published_at.isoformat(),
            "effective_at": record.effective_at.isoformat() if record.effective_at else None,
        }
    )
    return NormalizedLegalProvisionRecord(
        id=source_uuid(SourceType.LEGAL_PROVISION, normalized_text["record_id"]),
        record_id=normalized_text["record_id"],
        regulation_name=normalized_text["regulation_name"],
        article_number=normalized_text["article_number"],
        content=normalized_text["content"],
        issuing_authority=normalized_text["issuing_authority"],
        published_at=record.published_at,
        effective_at=record.effective_at,
        legal_status=record.legal_status,
        source_kind=record.source_kind,
        source_title=normalized_text["source_title"],
        source_description=normalized_text["source_description"],
        source_url=str(record.source_url),
        publisher=normalized_text["publisher"],
        is_demo=False,
        is_synthetic=False,
        collected_at=record.collected_at,
        authorization_note=normalized_text["authorization_note"],
        content_hash=content_hash,
    )


def _reject_batch_duplicates(records: Iterable[object], *, identity: str) -> None:
    identifiers: set[object] = set()
    hashes: set[object] = set()
    for record in records:
        identifier = getattr(record, identity)
        content_hash = getattr(record, "content_hash")
        if identifier in identifiers:
            raise ImportConflictError(f"Duplicate {identity} in import batch")
        if content_hash in hashes:
            raise ImportConflictError("Duplicate normalized content in import batch")
        identifiers.add(identifier)
        hashes.add(content_hash)


def import_cases(database: Database, records: Iterable[CaseSourceRecord]) -> ImportSummary:
    normalized = [normalize_case(record) for record in records]
    if not normalized:
        raise DataImportError("Case import batch is empty")
    _reject_batch_duplicates(normalized, identity="case_number")

    created = 0
    skipped = 0
    try:
        with database.session() as session, session.begin():
            for record in normalized:
                existing_by_number = session.scalar(
                    select(Case).where(Case.case_number == record.case_number)
                )
                if existing_by_number is not None:
                    if existing_by_number.content_hash != record.content_hash:
                        raise ImportConflictError("Case identifier already has different content")
                    skipped += 1
                    continue

                existing_by_hash = session.scalar(
                    select(Case).where(Case.content_hash == record.content_hash)
                )
                if existing_by_hash is not None:
                    raise ImportConflictError("Case content already exists under another identifier")

                session.add(Case(**record.model_dump(mode="python")))
                created += 1
    except ImportConflictError:
        raise
    except SQLAlchemyError as exc:
        raise DataImportError("Case import database operation failed") from exc

    return ImportSummary(received=len(normalized), created=created, skipped=skipped)


def import_legal_provisions(
    database: Database,
    records: Iterable[LegalProvisionSourceRecord],
) -> ImportSummary:
    normalized = [normalize_legal_provision(record) for record in records]
    if not normalized:
        raise DataImportError("Legal-provision import batch is empty")
    _reject_batch_duplicates(normalized, identity="record_id")

    created = 0
    skipped = 0
    try:
        with database.session() as session, session.begin():
            for record in normalized:
                existing_by_id = session.scalar(
                    select(LegalProvision).where(
                        LegalProvision.record_id == record.record_id
                    )
                )
                if existing_by_id is not None:
                    if existing_by_id.content_hash != record.content_hash:
                        raise ImportConflictError(
                            "Legal-provision identifier already has different content"
                        )
                    skipped += 1
                    continue
                if session.scalar(
                    select(LegalProvision.id).where(
                        LegalProvision.content_hash == record.content_hash
                    )
                ) is not None:
                    raise ImportConflictError(
                        "Legal-provision content already exists under another identifier"
                    )
                session.add(LegalProvision(**record.model_dump(mode="python")))
                created += 1
    except ImportConflictError:
        raise
    except SQLAlchemyError as exc:
        raise DataImportError("Legal-provision import database operation failed") from exc

    return ImportSummary(received=len(normalized), created=created, skipped=skipped)
