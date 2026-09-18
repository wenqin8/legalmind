import hashlib
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.legal_catalog import load_catalog, import_catalog, retrieve_provisions, event_interval

CATALOG = Path('data/legal/verified_provisions.jsonl')


def test_official_snapshots_match_every_article_and_hash():
    entries = load_catalog(CATALOG)
    assert len(entries) == 60
    assert {d for entry in entries for d in entry.verification.domains} == {'marriage_family', 'labor_dispute', 'traffic_accident', 'contract_dispute'}
    import json
    manifest = json.loads((CATALOG.parent / 'manifest.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        path = CATALOG.parent / source['snapshot']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        content = path.read_text(encoding='utf-8')
        for entry in entries:
            if str(entry.record.source_url) == source['source_url']:
                assert entry.verification.original_text in content
    raw = entries[0].model_dump(mode='json')
    raw['verification']['original_text'] += '伪造'
    with pytest.raises(ValidationError):
        type(entries[0]).model_validate(raw)


@pytest.mark.parametrize('domain,query,article', [
    ('labor_dispute', '公司拖欠工资，如何申请仲裁', '第二十七条'),
    ('marriage_family', '离婚后孩子抚养费应如何承担', '第一千零八十五条'),
    ('traffic_accident', '交通事故机动车行人责任赔偿保险', '第七十六条'),
    ('contract_dispute', '对方不履行合同应承担违约责任', '第五百七十七条'),
])
def test_four_domain_retrieval_is_independent_and_time_filtered(app, domain, query, article):
    entries = load_catalog(CATALOG)
    assert import_catalog(app.state.database, entries)['created'] == 60
    assert import_catalog(app.state.database, entries)['updated'] == 60
    rows = retrieve_provisions(app.state.database, query, domain, event_date='2025年6月1日')
    assert article in [row.article_number for row, _ in rows]
    assert all(domain in v.domains for _, v in rows)
    assert not retrieve_provisions(app.state.database, query, domain, event_date='1995年')
    assert not retrieve_provisions(app.state.database, query, domain, event_date=None)
    assert not retrieve_provisions(app.state.database, '今天的天气如何', domain, event_date='2025年')


@pytest.mark.parametrize('value,expected', [
    ('2025年', (date(2025, 1, 1), date(2025, 12, 31))),
    ('2025年2月', (date(2025, 2, 1), date(2025, 2, 28))),
    ('2025-02-02', (date(2025, 2, 2), date(2025, 2, 2))),
    ('2020年12月至2021年2月', (date(2020, 12, 1), date(2021, 2, 28))),
    ('去年', None), ('2025年2月30日', None),
])
def test_conservative_event_intervals(value, expected):
    assert event_interval(value) == expected


def test_cross_version_intervals_and_invalid_catalog_updates(app):
    entries = load_catalog(CATALOG)
    import_catalog(app.state.database, entries)
    assert not retrieve_provisions(app.state.database, '合同违约', 'contract_dispute', event_date='2020年12月至2021年2月')
    changed = entries[0].model_copy(deep=True)
    changed.record.content += '改动'
    with pytest.raises(ValueError):
        import_catalog(app.state.database, [changed])
