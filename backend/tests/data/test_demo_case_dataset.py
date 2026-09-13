import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.jsonl"
DOMAINS = {
    "marriage_family",
    "labor_dispute",
    "traffic_accident",
    "contract_dispute",
}
DEMO_ID_PATTERN = re.compile(
    r"^DEMO-(MARRIAGE_FAMILY|LABOR_DISPUTE|TRAFFIC_ACCIDENT|CONTRACT_DISPUTE)-\d{3}$"
)


def load_records() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_day_one_dataset_has_four_traceable_demo_cases_per_domain() -> None:
    records = load_records()

    assert len(records) == 16
    assert Counter(record["domain"] for record in records) == Counter(
        {domain: 4 for domain in DOMAINS}
    )
    assert len({record["demo_id"] for record in records}) == len(records)

    for record in records:
        demo_id = record["demo_id"]
        assert isinstance(demo_id, str)
        assert DEMO_ID_PATTERN.fullmatch(demo_id)
        assert record["case_number"] == demo_id
        assert record["source_type"] == "case"
        assert record["source_kind"] == "demo"
        assert record["source_title"] == "LegalMind 第二周演示案例集"
        assert record["source_description"] == (
            "课程演示合成数据，由项目根据常见争议要素编写，不对应任何真实案件。"
        )
        assert record["source_url"] is None
        assert record["court"] is None
        assert record["judgment_date"] is None
        assert record["law_references"] == []
        assert record["is_demo"] is True
        assert record["is_synthetic"] is True
        assert "不得作为真实案例" in str(record["authorization_note"])
        assert "法律依据" in str(record["authorization_note"])
        collected_at = datetime.fromisoformat(str(record["collected_at"]))
        assert collected_at.tzinfo is not None


def test_day_one_dataset_has_complete_non_duplicate_retrieval_text() -> None:
    records = load_records()
    required_text_fields = (
        "title",
        "summary",
        "facts",
        "dispute_focus",
        "reasoning",
    )

    for record in records:
        for field in required_text_fields:
            value = record[field]
            assert isinstance(value, str)
            assert value.strip()

    normalized_bodies = {
        "".join(str(record[field]).split())
        for record in records
        for field in ("facts", "dispute_focus", "reasoning")
    }
    assert len(normalized_bodies) == len(records) * 3
