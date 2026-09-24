"""Explicit identities for the frozen demo and isolated evaluation corpora."""

import hashlib
import json
from functools import lru_cache

from sqlalchemy import select

from app.core.config import BACKEND_DIR
from app.db.models import LegalProvision
from app.rag.legal_catalog import load_catalog

PROFILE_PATHS = {
    'demo-m3-60': ('data/legal/verified_provisions.jsonl',),
    'eval-rag-v1-197': ('data/legal/verified_provisions.jsonl', 'data/legal/expansion-v1/verified_provisions.jsonl'),
    'eval-rag-v2-209': ('data/legal/verified_provisions.jsonl', 'data/legal/expansion-v1/verified_provisions.jsonl',
                        'data/legal/traffic-ii-2026/verified_provisions.jsonl'),
}


def fingerprint(rows):
    return hashlib.sha256(json.dumps(sorted(rows), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def profile_entries(name):
    return [entry for path in PROFILE_PATHS[name] for entry in load_catalog(BACKEND_DIR / path)]


def signature(record_id, metadata):
    return (record_id, metadata['text_sha256'], metadata['version'], metadata['effective_from'],
            metadata.get('effective_until') or '', metadata['verified_at'], metadata['status_as_of'],
            metadata.get('temporal_rule', 'event_date'), metadata.get('transition_text') or '')


@lru_cache
def profile_fingerprints():
    return {name: fingerprint([signature(e.record.record_id, e.verification.model_dump(mode='json'))
                              for e in profile_entries(name)]) for name in PROFILE_PATHS}


def catalog_identity(database):
    with database.session() as session:
        rows = session.scalars(select(LegalProvision)).all()
        verified = [row for row in rows if row.verification]
        digest = fingerprint([signature(row.record_id, row.verification) for row in verified])
    name = next((name for name, expected in profile_fingerprints().items() if expected == digest and len(rows) == len(verified)), 'custom')
    return {'profile': name, 'provision_count': len(rows), 'fingerprint': digest}


def catalog_warning(database):
    data = catalog_identity(database)
    text = f"资料版本：{data['profile']}（{data['provision_count']}条法条）。"
    if data['profile'] == 'demo-m3-60':
        text += '当前为冻结演示版，未启用209条扩展评估资料；评估成绩不代表本演示版能力。'
    elif data['profile'].startswith('eval-'):
        text += '当前为扩展评估版，资料未构成完整现行法律库。'
    else:
        text += '自定义资料集，不适用冻结评估成绩。'
    return text
