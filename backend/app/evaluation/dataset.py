"""Frozen benchmark contracts and reproducibility checks."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import BACKEND_DIR
from app.rag.legal_catalog import load_catalog
from app.schemas.tasks import Domain

BENCHMARK_DIR = BACKEND_DIR / 'data/evaluation/rag-v1'
CATALOGS = (BACKEND_DIR / 'data/legal/verified_provisions.jsonl', BACKEND_DIR / 'data/legal/expansion-v1/verified_provisions.jsonl')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Judgment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    grade: int = Field(ge=1, le=3)
    rationale: str = Field(min_length=5)


class Query(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    route: Literal['case', 'law']
    domain: Domain
    split: Literal['development', 'holdout']
    scenario_group: str
    query: str = Field(min_length=5, max_length=1000)
    category: str
    event_date: str | None = None
    event_start: str | None = None
    event_end: str | None = None
    general: bool = False
    expected_behavior: Literal['answer', 'clarify', 'insufficient']
    relevance: dict[str, Judgment]
    annotation_note: str
    review_status: Literal['agent_draft_pending_expert'] = 'agent_draft_pending_expert'

    @model_validator(mode='after')
    def validate_answer(self):
        if (self.expected_behavior == 'answer') != bool(self.relevance):
            raise ValueError('Answerability must agree with relevance judgments')
        if bool(self.event_start) != bool(self.event_end):
            raise ValueError('Both date bounds are required')
        return self


def catalog_entries():
    return [entry for path in CATALOGS for entry in load_catalog(path)]


def load_queries(directory: Path = BENCHMARK_DIR) -> list[Query]:
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for relative, expected in manifest['files'].items():
        path = (BACKEND_DIR / relative).resolve()
        if not path.is_relative_to(BACKEND_DIR) or sha256(path) != expected:
            raise ValueError(f'Frozen artifact mismatch: {relative}')
    rows = [Query.model_validate_json(line) for line in (directory / 'queries.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    groups = {}
    known_laws = {entry.record.record_id for entry in catalog_entries()}
    known_cases = {json.loads(line)['case_number'] for line in (BACKEND_DIR/'data/demo/cases.jsonl').read_text(encoding='utf-8').splitlines()}
    if len({row.id for row in rows}) != len(rows):
        raise ValueError('Duplicate query ID')
    for row in rows:
        old = groups.setdefault(row.scenario_group, row.split)
        if old != row.split:
            raise ValueError('Scenario family crosses development and holdout')
        if not set(row.relevance).issubset(known_cases if row.route == 'case' else known_laws):
            raise ValueError('Unknown gold source')
    if len(rows) != 160 or sum(row.split == 'holdout' for row in rows) != 40:
        raise ValueError('Expected 160 queries, including 40 held-out queries')
    return rows
