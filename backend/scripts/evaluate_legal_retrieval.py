"""Reproduce statute candidate coverage separately from frozen M2 case rankings."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import BACKEND_DIR
from app.db.base import Base
from app.db.session import Database
from app.rag.legal_catalog import import_catalog, load_catalog, retrieve_provisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = BACKEND_DIR.parent / 'tmp' / ('legal-evaluation-' + uuid4().hex + '.db')
    target.parent.mkdir(exist_ok=True)
    database = Database(f'sqlite:///{target.as_posix()}')
    results = []
    try:
        Base.metadata.create_all(database.engine)
        import_catalog(database, load_catalog(BACKEND_DIR / 'data/legal/verified_provisions.jsonl'))
        for line in (BACKEND_DIR / 'data/evaluation/legal_queries.jsonl').read_text(encoding='utf-8').splitlines():
            item = json.loads(line)
            rows = retrieve_provisions(database, item['query'], item['domain'], event_date=item['event_date'])
            actual = [row.record_id for row, _ in rows]
            expected = item['expected_records']
            results.append({**item, 'actual_top_5': actual, 'passed':bool(set(actual) & set(expected)) if expected else not actual})
    finally:
        database.dispose()
    report = {'checked_at':datetime.now(timezone.utc).isoformat(), 'scope':'Candidate recall and version filtering only; not a legal reasoning accuracy measure',
              'total':len(results), 'passed_count':sum(item['passed'] for item in results), 'passed':all(item['passed'] for item in results), 'items':results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='items'}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
