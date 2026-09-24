import json
from pathlib import Path

import pytest

from scripts.evaluate_quality_gates import apply_gates


@pytest.fixture
def reports():
    root = Path('../docs/acceptance')
    return (json.loads((root / 'rag-v2-development-answers-run5.json').read_text(encoding='utf-8')),
            json.loads((root / 'rag-v2-development-retrieval.json').read_text(encoding='utf-8')))


def test_missing_semantic_review_cannot_pass(reports):
    raw, retrieval = reports
    result = apply_gates(raw, retrieval, None, 'actual')
    assert result['checks']['complete_runs']
    assert not result['checks']['semantic_review']
    assert not result['quality_gate_passed']


def test_review_is_bound_to_exact_raw_report(reports):
    raw, retrieval = reports
    initial = apply_gates(raw, retrieval, None, 'actual')
    notes = {'raw_report_sha256': 'other', 'turns': {
        key: {'faithfulness': 'pass', 'applicability': 'pass'} for key in initial['semantic_reviews']}}
    result = apply_gates(raw, retrieval, notes, 'actual')
    assert not result['checks']['semantic_review']
    notes['raw_report_sha256'] = 'actual'
    assert apply_gates(raw, retrieval, notes, 'actual')['checks']['semantic_review']


def test_subset_or_duplicate_retrieval_cannot_claim_complete(reports):
    raw, retrieval = reports
    retrieval['results'][-1] = retrieval['results'][0]
    result = apply_gates(raw, retrieval, None, 'actual')
    assert not result['checks']['complete_runs']
    assert not result['quality_gate_passed']


def test_seen_holdout_is_not_a_development_gate(reports):
    raw, retrieval = reports
    raw['scenarios'][0]['split'] = 'holdout'
    assert not apply_gates(raw, retrieval, None, 'actual')['checks']['development_only']
