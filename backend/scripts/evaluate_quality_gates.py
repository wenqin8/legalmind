"""Apply frozen development gates to immutable runs and explicit semantic reviews."""

import argparse
import json
from pathlib import Path

from app.core.config import BACKEND_DIR
from app.evaluation.dataset import sha256
from app.evaluation.dataset import BENCHMARK_DIR, load_queries
from scripts.review_rag_answers import review

GATES = BACKEND_DIR / 'data/evaluation/rag-v2/quality-gates.json'


def apply_gates(raw, retrieval, annotations, raw_digest):
    requirements = json.loads(GATES.read_text(encoding='utf-8'))
    inspected = review(raw)
    turns = [(s['id'], i, t) for s in inspected['items'] for i, t in enumerate(s['turns'], 1)]
    answers = [(sid, i, t) for sid, i, t in turns if t.get('evaluation', {}).get('observed_behavior') == 'answer']
    source_rows = [r for r in retrieval['results'] if r['route'] == 'law_bm25' and any(g == 3 for g in r['gold'].values())]
    direct_hits = sum(any(r['gold'].get(k) == 3 for k in r['ranking'][:5]) for r in source_rows)
    negatives = [t for _, _, t in turns if t['expected'] == 'insufficient']
    safe_count = sum(t.get('evaluation', {}).get('observed_behavior') in ('insufficient', 'clarify') for t in negatives)
    corrections = {}
    for sid in requirements['required_correction_scenarios']:
        selected = [t for name, _, t in turns if name == sid]
        corrections[sid] = (len(selected) == 3 and selected[1].get('evaluation', {}).get('observed_behavior') == 'conflict'
            and selected[1]['evaluation']['checks']['conflict_preserved']
            and selected[2].get('evaluation', {}).get('observed_behavior') == 'answer'
            and selected[2]['evaluation']['checks']['confirmed_field'])
    notes = (annotations or {}).get('turns', {})
    digest_matches = (annotations or {}).get('raw_report_sha256') == raw_digest
    semantic = {f'{sid}:{index}': digest_matches and notes.get(f'{sid}:{index}', {}).get('faithfulness') == 'pass'
                and notes.get(f'{sid}:{index}', {}).get('applicability') == 'pass'
                for sid, index, _ in answers}
    direct_rate = direct_hits / len(source_rows) if source_rows else None
    safe_rate = safe_count / len(negatives) if negatives else None
    expected_retrieval = {(q.id, route) for q in load_queries() if q.split == 'development'
                          for route in (('case_vector', 'case_bm25', 'case_hybrid') if q.route == 'case' else ('law_bm25',))}
    actual_retrieval = [(row['id'], row['route']) for row in retrieval['results']]
    frozen_scenarios = [json.loads(line) for line in (BENCHMARK_DIR / 'scenarios.jsonl').read_text(encoding='utf-8').splitlines()]
    expected_scenarios = {s['id']: s for s in frozen_scenarios if s['split'] == 'development'}
    scenarios_unchanged = {s['id'] for s in raw['scenarios']} == set(expected_scenarios) and all(
        s['query_id'] == expected_scenarios[s['id']]['query_id'] and
        [t['expected'] for t in s['turns']] == expected_scenarios[s['id']]['turns'] for s in raw['scenarios'])
    checks = {
        'development_only': raw.get('split') == 'development' and retrieval.get('split') == 'development'
            and all(s['split'] == 'development' for s in raw['scenarios']),
        'complete_runs': raw.get('complete') is True and retrieval.get('complete') is True
            and len(raw['scenarios']) == 36 and len(turns) == 52
            and scenarios_unchanged
            and len(actual_retrieval) == len(expected_retrieval) and set(actual_retrieval) == expected_retrieval
            and not any(row.get('error') for row in retrieval['results']),
        'direct_hit_at_5': direct_rate is not None and direct_rate >= requirements['direct_hit_at_5_minimum'],
        'behavior_match': inspected['metrics']['behavior_match_including_errors']['value'] >= requirements['behavior_match_minimum'],
        'safe_nonanswer': safe_rate == requirements['safe_nonanswer_minimum'],
        'four_corrections': all(corrections.values()),
        'structural_safety': not any(inspected['metrics']['hard_check_failures'].values()),
        'semantic_review': bool(answers) and all(semantic.values()),
        'same_evaluation_corpus': raw.get('catalog', {}).get('fingerprint') is not None and
            raw['catalog']['fingerprint'] == retrieval.get('catalog', {}).get('fingerprint'),
    }
    return {'scope': 'development_regression_not_blind_legal_certification', 'quality_gate_passed': all(checks.values()),
            'checks': checks, 'metrics': inspected['metrics'], 'corrections': corrections,
            'direct_hit_at_5': {'value': direct_rate, 'hits': direct_hits, 'denominator': len(source_rows)},
            'safe_nonanswer': {'value': safe_rate, 'safe': safe_count, 'denominator': len(negatives)},
            'semantic_reviews': semantic, 'reviewer': (annotations or {}).get('reviewer'),
            'expert_review': 'not performed', 'catalog': raw.get('catalog'), 'gate_definition_sha256': sha256(GATES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--answers', type=Path, required=True)
    parser.add_argument('--retrieval', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a new output path')
    raw = json.loads(args.answers.read_text(encoding='utf-8'))
    retrieval = json.loads(args.retrieval.read_text(encoding='utf-8'))
    notes = json.loads(args.reviews.read_text(encoding='utf-8')) if args.reviews else None
    report = apply_gates(raw, retrieval, notes, sha256(args.answers))
    report.update(raw_report_sha256=sha256(args.answers), retrieval_report_sha256=sha256(args.retrieval),
                  semantic_review_sha256=sha256(args.reviews) if args.reviews else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'quality_gate_passed': report['quality_gate_passed'], 'checks': report['checks']}, ensure_ascii=False))
    return 0 if report['quality_gate_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
