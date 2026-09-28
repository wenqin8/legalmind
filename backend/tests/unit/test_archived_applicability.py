"""Re-use actual run-11 JSON to exercise source-role normalization offline."""

import json
from pathlib import Path

import pytest

from app.agents.legal_evidence import legal_evidence
from app.llm.fake import FakeLLMClient
from app.rag.catalog_profiles import profile_entries
from app.rag.legal_catalog import import_catalog
from app.schemas.tasks import TaskState


@pytest.mark.anyio
@pytest.mark.parametrize('scenario_id', ['E-L-TA-03', 'E-L-CD-02'])
async def test_real_recorded_role_overlap_preserves_every_selected_span(app, scenario_id):
    path = Path(__file__).resolve().parents[3]/'docs/acceptance/rag-v2-targeted-run11.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    scenario = next(s for s in raw['scenarios'] if s['id'] == scenario_id)
    turn = scenario['turns'][0]
    assert turn['status'] == 424
    call = next(c for c in turn['model_trace'] if c['task'] == 'TASK:APPLICABILITY')
    selection = json.loads(call['output'])
    assert set(selection['direct_support']) & set(selection['supporting_support'])
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))

    class ArchivedJSON(FakeLLMClient):
        async def complete(self, messages):
            # Test the captured JSON's interpretation, not the new prompt's efficacy.
            data = json.loads(messages[1].content)
            assert data == call['input']
            return call['output']

    result = await legal_evidence(app.state.database, call['input']['query'],
        TaskState(kind='qa', mode='general', domain=scenario['domain']), ArchivedJSON())
    assert result.status == 'answer'
    assert {str(e.source.source_id) for e in result.evidence} == set(selection['source_ids'])
    for item in result.evidence:
        key = str(item.source.source_id)
        expected = set(selection['direct_support'].get(key, [])) | set(selection['supporting_support'].get(key, []))
        assert set(item.support_span_ids) == expected
        assert item.role == ('direct' if key in selection['direct_support'] else 'supporting')
