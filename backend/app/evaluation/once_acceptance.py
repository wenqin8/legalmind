"""Immutable fresh candidate packages with a one-shot observation receipt."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import BACKEND_DIR
from app.evaluation.dataset import Query, sha256


def implementation_digest():
    root = BACKEND_DIR.parent
    files = [p for directory in (BACKEND_DIR/'app', BACKEND_DIR/'scripts', root/'frontend/src')
             for p in directory.rglob('*') if p.suffix in {'.py','.ts','.vue','.css'}]
    files += [root/'frontend/package-lock.json', root/'frontend/package.json', root/'frontend/Dockerfile',
              BACKEND_DIR/'requirements.txt', BACKEND_DIR/'constraints.txt', BACKEND_DIR/'Dockerfile',
              root/'compose.yml', root/'deployment/nginx.conf']
    hashes = {p.relative_to(root).as_posix():sha256(p) for p in sorted(files)}
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()


def load_package(directory: Path, *, require_frozen_implementation=True):
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if require_frozen_implementation and manifest['implementation_sha256'] != implementation_digest():
        raise ValueError('Implementation changed after package freeze; create another package')
    for name, digest in manifest['files'].items():
        file = (directory/name).resolve()
        if not file.is_relative_to(directory.resolve()) or sha256(file) != digest:
            raise ValueError('Acceptance package fingerprint mismatch')
    queries = [Query.model_validate_json(line) for line in (directory/'queries.jsonl').read_text(encoding='utf-8').splitlines()]
    scenarios = [json.loads(line) for line in (directory/'scenarios.jsonl').read_text(encoding='utf-8').splitlines()]
    if len({q.id for q in queries}) != len(queries) or len({s['id'] for s in scenarios}) != len(scenarios) or len(queries)!=manifest['query_count']:
        raise ValueError('Invalid acceptance package IDs/counts')
    query_ids = {q.id for q in queries}
    if any(s['query_id'] not in query_ids or s['split'] != 'acceptance' for s in scenarios):
        raise ValueError('Invalid acceptance scenario references')
    if len(scenarios) != manifest.get('scenario_count', len(queries)):
        raise ValueError('Invalid acceptance scenario count')
    by_id = {q.id: q for q in queries}
    for scenario in scenarios:
        query = by_id[scenario['query_id']]
        if (query.split != 'acceptance' or scenario['domain'] != query.domain
                or scenario['turns'] != [{'message': query.query, 'expected': query.expected_behavior}]
                or set(scenario['gold_sources']) != set(query.relevance)):
            raise ValueError('Acceptance scenario does not match its frozen query')
    return manifest, queries, scenarios


def load_observed_package(directory: Path):
    """Replay consumed questions as development, never create another receipt."""
    receipt_path = directory / 'observation-receipt.json'
    if not receipt_path.exists():
        raise ValueError('Observed development requires a first-observation receipt')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('manifest_sha256') != sha256(directory/'manifest.json'):
        raise ValueError('First-observation receipt does not match the package')
    manifest, queries, scenarios = load_package(directory, require_frozen_implementation=False)
    return manifest, queries, scenarios


def consume_package(directory: Path, output: Path):
    manifest, queries, scenarios = load_package(directory)
    receipt = {'observed_at':datetime.now(timezone.utc).isoformat(), 'output':str(output.resolve()),
               'manifest_sha256':sha256(directory/'manifest.json'),
               'status':'consumed_before_execution', 'reason':'A failed or partial run is still preserved; this package cannot become unseen again.'}
    with (directory/'observation-receipt.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)
    return manifest, queries, scenarios
