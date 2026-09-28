"""Complementary evidence must be retrieved and actually used, never appended for metrics."""

import json
from pathlib import Path

import pytest

from app.rag.catalog_profiles import profile_entries
from app.rag.legal_catalog import import_catalog, retrieve_provisions
from app.agents.evidence import Evidence
from app.agents.qa import generate_qa
from app.core.errors import ModelUnavailableError
from tests.agent_helpers import AgentLLM
from tests.unit.test_grounding import evidence


@pytest.mark.parametrize('scenario_id,required', [
    ('E-L-TA-03',
     {'personal_injury-2022-04-24-8', 'civil_code-2020-05-28-1179'}),
    ('E-L-MF-03',
     {'marriage_ii-2025-01-15-8', 'civil_code-2020-05-28-1087'}),
    ('E-L-LD-01',
     {'labor_ii-2025-07-31-19', 'labor_contract-2012-12-28-38'}),
])
def test_related_primary_law_is_not_crowded_out(app, scenario_id, required):
    report = json.loads((Path(__file__).resolve().parents[3] /
                         'docs/acceptance/rag-v2-development-answers-run9.json').read_text(encoding='utf-8'))
    scenario = next(s for s in report['scenarios'] if s['id'] == scenario_id)
    payload = next(c['input'] for c in scenario['turns'][0]['model_trace'] if c['task'] == 'TASK:APPLICABILITY')
    query = '\n'.join(dict.fromkeys(v for v in (payload['query'], payload['facts'].get('facts')) if v))
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))
    rows = retrieve_provisions(app.state.database, query, scenario['domain'], event_date=None, general=True)
    assert len(rows) <= 5
    assert required <= {row.record_id for row, _ in rows}


class CoverageLLM(AgentLLM):
    def __init__(self, supplement='补充说明\n应当提供证明材料[S2]。', reject=False):
        super().__init__()
        self.response = '结论\n应当提供证明材料[S1]。\n\n风险\n资料尚未核实。\n\n下一步\n请整理材料。'
        self.supplement = supplement
        self.reject = reject
        self.coverage_calls = []

    async def complete(self, messages):
        data = json.loads(messages[1].content)
        if messages[0].content.startswith('TASK:COVERAGE'):
            self.coverage_calls.append(data)
            return self.supplement
        if self.reject and messages[0].content.startswith('TASK:CONDITIONS') and '补充说明' in data['paragraph']:
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported'} for u in data['units']]})
        return await super().complete(messages)


def coverage_evidence():
    first = evidence()[0]
    from uuid import uuid4
    second = Evidence(first.source.model_copy(update={'source_id': uuid4(), 'citation_id': 'S2'}), first.text,
                      'supporting', (0,))
    return [Evidence(first.source, first.text, 'direct', (0,)), second]


@pytest.mark.anyio
async def test_selected_source_omission_gets_one_verified_supplement():
    model = CoverageLLM()
    parts = [p async for p in generate_qa('材料', [], coverage_evidence(), model)]
    assert len(model.coverage_calls) == 1
    assert model.coverage_calls[0]['missing_citations'] == ['S2']
    assert '[S2]' in parts[-2] and '参考材料' not in parts[-2]
    assert '[S2]' in parts[-1]


@pytest.mark.anyio
@pytest.mark.parametrize('supplement,reject', [
    ('补充说明\n只有编号没有法律内容[S2]。', True),
    ('补充说明\n应当提供材料[S9]。', False),
    ('补充说明\n请整理材料。', False),
])
async def test_invalid_supplement_is_not_appended_or_retried(supplement, reject):
    model = CoverageLLM(supplement, reject)
    parts = []
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa('材料', [], coverage_evidence(), model):
            parts.append(part)
    assert len(model.coverage_calls) == 1
    assert all('补充说明' not in p and '参考材料' not in p for p in parts)


@pytest.mark.anyio
async def test_already_used_sources_do_not_trigger_an_extra_call():
    model = CoverageLLM()
    model.response = model.response.replace('[S1]', '[S1][S2]')
    _ = [p async for p in generate_qa('材料', [], coverage_evidence(), model)]
    assert not model.coverage_calls


def test_diagnostic_assigns_each_loss_to_its_observed_stage():
    from scripts.diagnose_source_losses import lost_between
    gold = {'direct': 3, 'support': 2, 'background': 1}
    assert lost_between(gold, ['direct', 'support'], ['direct']) == ['support']
    assert lost_between(gold, ['direct'], []) == ['direct']
    assert lost_between(gold, ['unrelated'], []) == []


@pytest.mark.parametrize('selection', [[], ['unknown'], ['E-L-MF-04', 'E-L-MF-04']])
def test_targeted_acceptance_refuses_invalid_selection(selection):
    from scripts.evaluate_rag_answers import select_scenarios
    with pytest.raises(ValueError):
        select_scenarios('development', selection)


def test_targeted_acceptance_retains_all_turns_without_running_other_scenarios():
    from scripts.evaluate_rag_answers import select_scenarios
    rows = select_scenarios('development', ['E-L-MF-05'])
    assert len(rows) == 1 and rows[0]['id'] == 'E-L-MF-05' and len(rows[0]['turns']) == 2


@pytest.mark.anyio
@pytest.mark.parametrize('mode', ['valid', 'missing_support', 'dropped_source', 'overlap', 'unknown_span', 'invalid_direct_hidden_by_support', 'schema_echo', 'schema_true', 'unknown_extra'])
async def test_selection_preserves_only_explicitly_grounded_direct_and_supporting_sources(app, mode):
    from app.agents.legal_evidence import legal_evidence
    from app.llm.fake import FakeLLMClient
    from app.schemas.tasks import TaskState
    import_catalog(app.state.database, profile_entries('eval-rag-v2-209'))

    class Selector(FakeLLMClient):
        async def complete(self, messages):
            candidates = json.loads(messages[1].content)['candidates']
            first, second = candidates[:2]
            result = {'assessment': 'general', 'source_ids': [first['source_id'], second['source_id']],
                'direct_support': {first['source_id']: [0]}, 'supporting_support': {second['source_id']: [0]}}
            if mode == 'missing_support':
                result['supporting_support'] = {}
            if mode == 'dropped_source':
                result['source_ids'] = [first['source_id']]
            if mode == 'overlap':
                result['supporting_support'][first['source_id']] = [0]
            if mode == 'unknown_span':
                result['supporting_support'][second['source_id']] = [99999]
            if mode == 'invalid_direct_hidden_by_support':
                result['direct_support'][first['source_id']] = [99999]
                result['supporting_support'][first['source_id']] = [0]
            if mode in {'schema_echo', 'schema_true'}:
                result['additionalProperties'] = mode == 'schema_true'
            if mode == 'unknown_extra':
                result['unverified_decision'] = True
            return json.dumps(result)

    call = legal_evidence(app.state.database, '护理人数和护理费',
                          TaskState(kind='qa', mode='general', domain='traffic_accident'), Selector())
    if mode in {'valid', 'overlap', 'schema_echo'}:
        result = await call
        assert result.status == 'answer'
        assert [e.role for e in result.evidence] == ['direct', 'supporting']
        assert all(e.support_span_ids == (0,) for e in result.evidence)
    else:
        with pytest.raises(ModelUnavailableError):
            await call
