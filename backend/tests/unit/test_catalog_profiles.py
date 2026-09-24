import hashlib
import json
from pathlib import Path

from app.rag.catalog_profiles import catalog_identity, profile_entries
from app.rag.legal_catalog import import_catalog, load_catalog, retrieve_provisions


def test_traffic_official_snapshot_and_transition_rule():
    root = Path('data/legal/traffic-ii-2026')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    catalog = root / 'verified_provisions.jsonl'
    assert hashlib.sha256(catalog.read_bytes()).hexdigest() == manifest['catalog_sha256']
    assert hashlib.sha256((root / manifest['snapshot']).read_bytes()).hexdigest() == manifest['snapshot_sha256']
    text = (root / manifest['snapshot']).read_text(encoding='utf-8')
    entries = load_catalog(catalog)
    assert len(entries) == 12
    for entry in entries:
        assert entry.verification.original_text in text
        assert entry.verification.temporal_rule == 'pending_after_effective'
        assert entry.verification.transition_text == entries[-1].verification.original_text


def test_explicit_profiles_and_pending_case_temporal_boundary(app):
    import_catalog(app.state.database, profile_entries('demo-m3-60'))
    assert catalog_identity(app.state.database)['profile'] == 'demo-m3-60'
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))
    assert catalog_identity(app.state.database)['profile'] == 'eval-rag-v2-209'
    query = '交通事故超过退休年龄仍有误工损失'
    def ids(**kwargs):
        return [r.record_id for r, _ in retrieve_provisions(app.state.database, query, 'traffic_accident', **kwargs)]
    target = 'traffic_ii-2026-05-06-6'
    assert target in ids(event_date='2026年7月1日')
    assert target not in ids(event_date='2026年5月1日')
    assert target in ids(event_date='2026年5月1日', case_status='目前尚未终审')
    assert target not in ids(event_date='2026年5月1日', case_status='2026年5月已经终审，现在申请再审')
