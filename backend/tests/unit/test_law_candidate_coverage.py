from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.rag.legal_catalog import diversify_provisions
from app.schemas.tasks import GroundedValue, TaskState
from app.llm.fake import FakeLLMClient


def test_diversity_retains_top_three_and_considers_other_positive_regulations():
    ranked = [((SimpleNamespace(record_id=str(i), regulation_name=name), None), score)
              for i, (name, score) in enumerate([
                  ('interpretation', 100), ('interpretation', 80), ('interpretation', 70),
                  ('interpretation', 60), ('interpretation', 50), ('general_law', 40), ('unrelated', 0)])]
    selected = diversify_provisions(ranked)
    assert [row.record_id for row, _ in selected] == ['0', '1', '2', '5', '3']
    assert len(ranked) == 7
    assert diversify_provisions([]) == []
    assert len(diversify_provisions(ranked[:2])) == 2


@pytest.mark.anyio
async def test_temporal_metadata_is_a_filter_not_extra_search_keywords(monkeypatch):
    from app.agents import legal_evidence as module
    captured = {}
    def retrieve(database, query, domain, **kwargs):
        captured.update(query=query, domain=domain, **kwargs)
        return []
    monkeypatch.setattr(module, 'retrieve_provisions', retrieve)
    def field(value):
        return GroundedValue(value=value, quote=value, source_turn_id=uuid4())
    task = TaskState(kind='qa', domain='traffic_accident', fields={
        'facts': field('护理费用如何确定'), 'event_date': field('2026年7月1日'),
        'case_status': field('尚未终审'), 'context': field('事故认定书已经出具')})
    await module.legal_evidence(None, '确认修改', task, FakeLLMClient())
    assert captured['query'] == '确认修改\n护理费用如何确定'
    assert captured['event_date'] == '2026年7月1日'
    assert captured['case_status'] == '尚未终审'


@pytest.mark.anyio
@pytest.mark.parametrize('selection,expected', [([0, 1], 'answer'), ([9999], 'error'), ([], 'error'), ([True], 'error')])
async def test_applicability_uses_only_server_span_ids(app, selection, expected):
    import json
    from app.agents.legal_evidence import legal_evidence
    from app.rag.legal_catalog import import_catalog
    from app.rag.catalog_profiles import profile_entries
    from app.core.errors import ModelUnavailableError
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))
    class Selector(FakeLLMClient):
        async def complete(self, messages):
            data = json.loads(messages[1].content)
            item = next(c for c in data['candidates'] if '无需缴纳社会保险费' in c['source']['original_text'])
            return json.dumps({'assessment': 'general', 'source_ids': [item['source_id']],
                               'direct_support': {item['source_id']: selection}})
    call = legal_evidence(app.state.database, '单位承诺不缴社保和补缴后补偿返还',
                          TaskState(kind='qa', mode='general', domain='labor_dispute'), Selector())
    if expected == 'error':
        with pytest.raises(ModelUnavailableError):
            await call
    else:
        assert (await call).status == expected
