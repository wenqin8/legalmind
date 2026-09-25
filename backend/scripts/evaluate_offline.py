"""Daily offline regression: tests, frozen retrieval and optional archived scoring."""

import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import BACKEND_DIR
from app.db.base import Base
from app.db.session import Database
from app.evaluation.dataset import load_queries, sha256
from app.evaluation.metrics import aggregate, ranking_metrics
from app.evaluation.offline_guard import OfflineGuard
from app.rag.catalog_profiles import profile_entries, catalog_identity
from app.rag.legal_catalog import import_catalog, retrieve_provisions

QUICK_TESTS = [
    'tests/unit/test_rag_blockers.py', 'tests/unit/test_law_candidate_coverage.py',
    'tests/unit/test_grounding.py', 'tests/unit/test_paragraph_context.py',
    'tests/unit/test_traffic_transition.py', 'tests/unit/test_tasks.py',
    'tests/unit/test_evaluation_answers.py', 'tests/unit/test_offline_evaluation.py',
    'tests/unit/test_evidence_coverage.py', 'tests/unit/test_archived_validation.py',
    'tests/integration/test_grounded_stream.py', 'tests/integration/test_multiturn_laws.py',
]


def evaluate_laws():
    database = Database('sqlite://')
    try:
        Base.metadata.create_all(database.engine)
        import_catalog(database, profile_entries('eval-rag-v2-209'))
        results = []
        for query in load_queries():
            if query.split != 'development' or query.route != 'law':
                continue
            started = time.perf_counter()
            rows = retrieve_provisions(database, query.query, query.domain,
                                       event_date=query.event_date, general=query.general)
            ranking = [row.record_id for row, _ in rows]
            gold = {key: value.grade for key, value in query.relevance.items()}
            results.append({'id': query.id, 'route': 'law_bm25', 'domain': query.domain,
                'answerable': bool(gold), 'ranking': ranking, 'gold': gold, 'error': None,
                'latency_ms': (time.perf_counter() - started) * 1000,
                'metrics': {str(k): ranking_metrics(ranking, gold, k) for k in (1, 3, 5)}})
        positives = [row for row in results if any(g == 3 for g in row['gold'].values())]
        hits = sum(any(row['gold'].get(key) == 3 for key in row['ranking']) for row in positives)
        return {'scope': 'frozen development laws; gold domain supplied; no LLM',
                'catalog': catalog_identity(database), 'groups': {'law_bm25': aggregate(results)},
                'direct_hit_at_5': {'hits': hits, 'denominator': len(positives),
                                    'value': hits/len(positives) if positives else None}, 'results': results}
    finally:
        database.dispose()


def run_tests(workspace, suite):
    xml_path = workspace / 'pytest.xml'
    network_path = workspace / 'pytest-network.json'
    env = {**os.environ, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'PYTHONIOENCODING': 'utf-8',
           'LEGALMIND_OFFLINE_NETWORK_REPORT': str(network_path)}
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'app.evaluation.offline_guard',
               '--junitxml', str(xml_path), *(QUICK_TESTS if suite == 'quick' else ['tests'])]
    process = subprocess.run(command, cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=300)
    (workspace / 'pytest-output.txt').write_text(process.stdout + process.stderr, encoding='utf-8')
    counts = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    if xml_path.exists():
        for node in ET.parse(xml_path).getroot().iter('testsuite'):
            for name in counts:
                counts[name] += int(node.get(name, '0'))
    network = json.loads(network_path.read_text(encoding='utf-8')) if network_path.exists() else None
    return {**counts, 'exit_code': process.returncode, 'network': network,
            'passed': process.returncode == 0 and counts['tests'] > 0 and network == {'blocked_attempts': 0},
            'details_directory': str(workspace)}


def run(*, suite, include_vectors=False, recording=None):
    workspace = BACKEND_DIR.parent / 'tmp' / ('offline-' + uuid4().hex)
    workspace.mkdir(parents=True)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'scope': 'offline_code_regression',
              'real_model_calls': 0, 'real_model_quality_passed': None, 'suite': suite,
              'limitations': ['Scripted/replayed outputs do not predict new model answers or validate prompt improvements.',
                  'Archived metrics describe only that immutable recording, not the current workflow.',
                  'Mock Redis verifies application behavior; real Redis acceptance is separate.',
                  'Local TCP tests verify transport timing/cancellation, not provider latency.']}
    guard = OfflineGuard()
    try:
        report['tests'] = run_tests(workspace, suite)
        with guard:
            if include_vectors:
                from scripts.evaluate_rag import evaluate
                report['retrieval'] = evaluate('development', 'eval-rag-v2-209')
                rows = [r for r in report['retrieval']['results'] if r['route']=='law_bm25' and any(g==3 for g in r['gold'].values())]
                report['retrieval']['direct_hit_at_5'] = {'hits': sum(any(r['gold'].get(k)==3 for k in r['ranking']) for r in rows),
                    'denominator': len(rows), 'value': sum(any(r['gold'].get(k)==3 for k in r['ranking']) for r in rows)/len(rows)}
            else:
                report['retrieval'] = evaluate_laws()
            if recording:
                from scripts.review_rag_answers import review
                raw = json.loads(recording.read_text(encoding='utf-8'))
                report['archived_answers'] = {'source': str(recording), 'sha256': sha256(recording),
                    'current_model_measurement': False, 'review': review(raw)}
        report['offline_regression_passed'] = (report['tests']['passed']
            and report['retrieval']['direct_hit_at_5']['value'] >= .9
            and not any(r.get('error') for r in report['retrieval']['results']) and not guard.attempts)
    except Exception as exc:
        report['failure_type'] = type(exc).__name__
        report['offline_regression_passed'] = False
    report['external_requests_blocked'] = len(guard.attempts)
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    report['implementation_files'] = {p.relative_to(BACKEND_DIR).as_posix(): sha256(p)
        for folder in ('app/agents', 'app/rag', 'app/evaluation', 'scripts') for p in sorted((BACKEND_DIR/folder).glob('*.py'))}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--suite', choices=['quick', 'full'], default='full')
    parser.add_argument('--include-vectors', action='store_true', help='Use cached local BGE weights; never download')
    parser.add_argument('--recording', type=Path, help='Re-score saved outputs without regenerating them')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a new output path; previous evidence is immutable')
    report = run(suite=args.suite, include_vectors=args.include_vectors, recording=args.recording)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report.get(key) for key in ('offline_regression_passed', 'real_model_calls',
          'real_model_quality_passed', 'tests', 'failure_type')}, ensure_ascii=False))
    return 0 if report['offline_regression_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
