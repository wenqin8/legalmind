import hashlib
import json
from collections import Counter
from pathlib import Path

from app.core.enums import LegalDomain
from app.rag.importer import load_case_records

EVALUATION_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evaluation" / "week2_queries.jsonl"
)
CASES_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.jsonl"


def _queries() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in EVALUATION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_week2_evaluation_set_is_frozen_and_balanced() -> None:
    queries = _queries()
    domains = Counter(query["domain"] for query in queries)

    assert len(queries) == 20
    assert len({query["query_id"] for query in queries}) == 20
    assert domains == Counter({domain.value: 5 for domain in LegalDomain})
    assert all(isinstance(query["query"], str) and query["query"].strip() for query in queries)


def test_evaluation_labels_reference_only_frozen_demo_cases() -> None:
    known_ids = {record.case_number for record in load_case_records(CASES_PATH)}

    for query in _queries():
        labels = query["relevant_case_ids"]
        assert isinstance(labels, list) and labels
        assert set(labels) <= known_ids


def test_evaluation_file_hash_is_frozen() -> None:
    digest = hashlib.sha256(EVALUATION_PATH.read_bytes()).hexdigest().upper()

    assert digest == "DAE562F49CDD93E8B3076B4464F7F4729114C55F5F68BD828AD6817BE4A2AB81"
