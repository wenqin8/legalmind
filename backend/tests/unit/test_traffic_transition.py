import json
from uuid import uuid4

import pytest

from app.agents.legal_evidence import legal_evidence
from app.rag.catalog_profiles import profile_entries
from app.rag.legal_catalog import import_catalog
from app.schemas.tasks import GroundedValue, TaskState


class RetirementEvidenceModel:
    async def complete(self, messages):
        payload = json.loads(messages[1].content)
        selected = [item for item in payload['candidates'] if '退休年龄' in item['source']['original_text']]
        return json.dumps({'assessment': 'conditional' if selected else 'insufficient',
                           'source_ids': [item['source_id'] for item in selected],
                           'direct_support': {item['source_id']: item['source']['original_text'] for item in selected}})


@pytest.mark.anyio
@pytest.mark.parametrize('event_date,status,expected', [
    ('2026年5月1日', None, 'clarify'),
    ('2026年5月1日', '不知道是否尚未终审', 'clarify'),
    ('2026年5月1日', '不是未终审', 'clarify'),
    ('2026年5月1日', '不清楚是否已经终审', 'clarify'),
    ('2026年5月1日', '目前尚未终审', 'answer'),
    ('2026年5月1日', '2026年5月已经终审，现在申请再审', 'insufficient'),
    ('2026年7月1日', None, 'answer'),
])
async def test_transition_requires_grounded_case_status(app, event_date, status, expected):
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))
    values = {'event_date': event_date, 'facts': '交通事故超过退休年龄仍有误工损失'}
    if status:
        values['case_status'] = status
    task = TaskState(kind='qa', domain='traffic_accident', fields={
        key: GroundedValue(value=value, quote=value, source_turn_id=uuid4()) for key, value in values.items()
    })
    result = await legal_evidence(app.state.database, values['facts'], task, RetirementEvidenceModel())
    assert result.status == expected
    if expected == 'clarify':
        assert list(result.missing) == ['case_status']
        assert result.evidence == []
    elif expected == 'answer':
        assert result.evidence and all(item.source.transition_text for item in result.evidence)
