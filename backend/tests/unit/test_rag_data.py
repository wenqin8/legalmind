from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.enums import ImportStatus
from app.db.base import Base
from app.db.models import Case, LegalProvision
from app.db.session import Database
from app.rag.importer import (
    ImportConflictError,
    import_cases,
    import_legal_provisions,
    load_case_records,
    normalize_case,
)
from app.rag.normalization import normalize_text
from app.rag.schemas import CaseSourceRecord, LegalProvisionSourceRecord

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.jsonl"


@pytest.fixture
def knowledge_database(tmp_path: Path):
    database = Database(f"sqlite:///{(tmp_path / 'knowledge.db').as_posix()}")
    Base.metadata.create_all(database.engine)
    try:
        yield database
    finally:
        database.dispose()


def valid_demo_payload() -> dict[str, object]:
    return load_case_records(DATASET_PATH)[0].model_dump(mode="json")


@pytest.mark.parametrize(
    "changes",
    [
        {"unexpected": "value"},
        {"source_type": "legal_provision"},
        {"domain": "criminal"},
        {"source_kind": "official"},
        {"source_url": "https://example.com/fake"},
        {"court": "虚构法院"},
        {"judgment_date": "2026-09-13"},
        {"law_references": ["未经核验的条文"]},
        {"is_demo": False},
        {"is_synthetic": False},
        {"collected_at": "2026-09-13T16:09:08"},
    ],
)
def test_demo_case_schema_rejects_invalid_or_invented_metadata(
    changes: dict[str, object],
) -> None:
    payload = valid_demo_payload()
    payload.update(changes)

    with pytest.raises(ValidationError):
        CaseSourceRecord.model_validate(payload)


def test_normalization_and_identifiers_are_deterministic() -> None:
    record = load_case_records(DATASET_PATH)[0]
    normalized = normalize_case(record)
    repeated = normalize_case(record)

    assert normalize_text("  Ａ\r\n\r\n   示例  ") == "A\n\n示例"
    assert normalized.id == repeated.id
    assert normalized.content_hash == repeated.content_hash
    assert len(normalized.content_hash) == 64


def test_case_import_is_transactional_and_idempotent(knowledge_database: Database) -> None:
    records = load_case_records(DATASET_PATH)

    first = import_cases(knowledge_database, records)
    second = import_cases(knowledge_database, records)

    assert first.model_dump() == {"received": 16, "created": 16, "skipped": 0}
    assert second.model_dump() == {"received": 16, "created": 0, "skipped": 16}
    with knowledge_database.session() as session:
        cases = session.scalars(select(Case).order_by(Case.case_number)).all()
        assert len(cases) == 16
        assert all(case.import_status == ImportStatus.PENDING for case in cases)
        assert all(case.court is None and case.source_url is None for case in cases)


def test_case_import_rejects_conflicting_identifier_without_partial_writes(
    knowledge_database: Database,
) -> None:
    records = load_case_records(DATASET_PATH)
    import_cases(knowledge_database, records[:1])
    changed_payload = records[0].model_dump(mode="json")
    changed_payload["title"] = "相同编号但不同内容"

    with pytest.raises(ImportConflictError, match="different content"):
        import_cases(
            knowledge_database,
            [records[1], CaseSourceRecord.model_validate(changed_payload)],
        )

    with knowledge_database.session() as session:
        assert session.scalar(select(func.count()).select_from(Case)) == 1


def test_case_import_rejects_duplicate_content_in_one_batch(
    knowledge_database: Database,
) -> None:
    record = load_case_records(DATASET_PATH)[0]
    duplicate_payload = deepcopy(record.model_dump(mode="json"))
    duplicate_payload["demo_id"] = "DEMO-MARRIAGE_FAMILY-099"
    duplicate_payload["case_number"] = "DEMO-MARRIAGE_FAMILY-099"

    with pytest.raises(ImportConflictError, match="Duplicate normalized content"):
        import_cases(
            knowledge_database,
            [record, CaseSourceRecord.model_validate(duplicate_payload)],
        )

    with knowledge_database.session() as session:
        assert session.scalar(select(func.count()).select_from(Case)) == 0


def test_verified_legal_provision_schema_and_import_are_available(
    knowledge_database: Database,
) -> None:
    record = LegalProvisionSourceRecord(
        record_id="OFFICIAL-TEST-ARTICLE-001",
        regulation_name="测试法规",
        article_number="第一条",
        content="仅用于验证法条结构，不进入演示语料。",
        issuing_authority="测试发布机关",
        published_at=date(2026, 1, 1),
        effective_at=date(2026, 2, 1),
        legal_status="effective",
        source_type="legal_provision",
        source_kind="official",
        source_title="测试来源",
        source_description="结构测试记录",
        source_url="https://example.com/verified-source",
        publisher="测试发布机关",
        collected_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        authorization_note="仅用于自动化结构测试。",
    )

    first = import_legal_provisions(knowledge_database, [record])
    second = import_legal_provisions(knowledge_database, [record])

    assert first.created == 1
    assert second.skipped == 1
    with knowledge_database.session() as session:
        provision = session.scalar(select(LegalProvision))
        assert provision is not None
        assert provision.import_status == ImportStatus.PENDING


@pytest.mark.parametrize(
    "changes",
    [
        {"source_url": None},
        {"source_kind": "demo"},
        {"legal_status": "unverified"},
        {"published_at": "not-a-date"},
        {"unknown_field": "value"},
    ],
)
def test_legal_provision_rejects_unverified_or_invalid_sources(
    changes: dict[str, object],
) -> None:
    payload = {
        "record_id": "OFFICIAL-TEST-ARTICLE-001",
        "regulation_name": "测试法规",
        "article_number": "第一条",
        "content": "仅用于验证法条结构，不进入演示语料。",
        "issuing_authority": "测试发布机关",
        "published_at": "2026-01-01",
        "effective_at": "2026-02-01",
        "legal_status": "effective",
        "source_type": "legal_provision",
        "source_kind": "official",
        "source_title": "测试来源",
        "source_description": "结构测试记录",
        "source_url": "https://example.com/verified-source",
        "publisher": "测试发布机关",
        "collected_at": "2026-09-13T00:00:00Z",
        "authorization_note": "仅用于自动化结构测试。",
    }
    payload.update(changes)

    with pytest.raises(ValidationError):
        LegalProvisionSourceRecord.model_validate(payload)


def test_case_import_rejects_stored_content_under_a_new_identifier(
    knowledge_database: Database,
) -> None:
    record = load_case_records(DATASET_PATH)[0]
    import_cases(knowledge_database, [record])
    duplicate_payload = deepcopy(record.model_dump(mode="json"))
    duplicate_payload["demo_id"] = "DEMO-MARRIAGE_FAMILY-099"
    duplicate_payload["case_number"] = "DEMO-MARRIAGE_FAMILY-099"

    with pytest.raises(ImportConflictError, match="another identifier"):
        import_cases(
            knowledge_database,
            [CaseSourceRecord.model_validate(duplicate_payload)],
        )

    with knowledge_database.session() as session:
        assert session.scalar(select(func.count()).select_from(Case)) == 1
