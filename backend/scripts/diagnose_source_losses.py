"""Attribute archived source losses and re-run retrieval with the same saved facts."""

import argparse
import json
from pathlib import Path
from statistics import mean

from app.db.base import Base
from app.db.session import Database
from app.evaluation.dataset import sha256
from app.evaluation.metrics import ranking_metrics
from app.evaluation.offline_guard import OfflineGuard
from app.rag.catalog_profiles import profile_entries
from app.rag.legal_catalog import import_catalog, retrieve_provisions
from scripts.review_rag_answers import review


def lost_between(gold, previous, following):
    return sorted(set(gold) & set(previous) - set(following))


def diagnose(path):
    raw = json.loads(path.read_text(encoding='utf-8'))
    archived = review(raw)
    rows = []
    database = Database('sqlite://')
    try:
        Base.metadata.create_all(database.engine)
        import_catalog(database, profile_entries('eval-rag-v2-209'))
        for scenario, scored in zip(raw['scenarios'], archived['items'], strict=True):
            gold = scored['gold_grades']
            for number, (turn, score) in enumerate(zip(scenario['turns'], scored['turns'], strict=True), 1):
                if turn['expected']['expected'] != 'answer':
                    continue
                stages = score.get('evaluation', score.get('stage_metrics', {}))
                candidate = stages.get('candidate_ids', [])
                selected = stages.get('selected_ids', [])
                returned = stages.get('returned_ids', [])
                calls = [c for c in turn.get('model_trace', []) if c['task'] == 'TASK:APPLICABILITY']
                current = []
                if calls:
                    data = calls[-1]['input']
                    facts = data['facts']
                    query = '\n'.join(dict.fromkeys(v for v in (data['query'], facts.get('facts')) if v))
                    hits = retrieve_provisions(database, query, scenario['domain'],
                        event_date=facts.get('event_date'), general=data['mode'] == 'general',
                        case_status=facts.get('case_status'), include_transition_questions=True)
                    current = [row.record_id for row, _ in hits]
                rows.append({'scenario_id': scenario['id'], 'turn': number, 'gold': gold,
                    'archived_status': turn.get('status'), 'archived_candidates': candidate,
                    'archived_selected': selected, 'archived_returned': returned,
                    'losses': {'retrieval': sorted(set(gold) - set(candidate)),
                               'selection': lost_between(gold, candidate, selected),
                               'generation': lost_between(gold, selected, returned)},
                    'current_candidates': current, 'current_missing': sorted(set(gold) - set(current)),
                    'current_candidate_metrics': ranking_metrics(current, gold, 5)})
    finally:
        database.dispose()
    return {'scope': 'current retrieval on archived development facts; selection/generation not re-run',
        'archive': path.as_posix(), 'archive_sha256': sha256(path), 'real_model_calls': 0,
        'current_final_source_recall': None, 'current_real_model_quality_passed': None,
        'archived_metrics': archived['metrics'],
        'current_candidate_recall': mean(row['current_candidate_metrics']['recall'] for row in rows),
        'current_candidate_hit': mean(row['current_candidate_metrics']['hit'] for row in rows),
        'expected_answer_turns': len(rows), 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a new output path')
    with OfflineGuard() as guard:
        report = diagnose(args.input)
    report['unexpected_network_attempts'] = len(guard.attempts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('expected_answer_turns', 'current_candidate_recall',
                                                  'current_candidate_hit', 'real_model_calls')}))


if __name__ == '__main__':
    main()
