"""Real missed claims and identifier failures, replayed without model/network."""

import json
from pathlib import Path

import pytest

from app.agents.claim_rules import deterministic_rejections
from app.agents.evidence import Evidence, validate_citations
from app.agents.grounding import GroundingViolation, sentence_units, validate_grounding
from app.agents.legal_references import normalize_cross_references
from app.agents.qa import FACT_RISK, checked_paragraph
from app.core.errors import ModelUnavailableError
from app.schemas.chat import SourceReference


def recorded(scenario_id):
    path = Path(__file__).resolve().parents[3] / 'docs/acceptance/rag-v2-targeted-run12.json'
    report = json.loads(path.read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == scenario_id)['turns'][0]
    trace = turn['model_trace']
    selection = next(c for c in trace if c['task'] == 'TASK:APPLICABILITY')
    selected = json.loads(selection['output'])['source_ids']
    evidence = [Evidence(SourceReference.model_validate(c['source']), c['source']['original_text'])
                for c in selection['input']['candidates'] if c['source_id'] in selected]
    return trace, evidence


class NoModel:
    async def complete(self, messages):
        raise AssertionError('A deterministic rejection must happen before model review')


@pytest.mark.anyio
@pytest.mark.parametrize('scenario_id,section', [('E-L-TA-03', '风险'), ('E-L-MF-04', '结论')])
async def test_recorded_false_accepts_are_rejected_before_model_review(scenario_id, section):
    trace, evidence = recorded(scenario_id)
    output = next(c['output'] for c in trace if c['task'] == 'TASK:QA')
    paragraph = next(p for p in output.split('\n\n') if p.startswith(section))
    with pytest.raises(GroundingViolation) as failure:
        await validate_grounding(paragraph, evidence, '材料', NoModel())
    assert failure.value.reason == 'unsupported_logic'


@pytest.mark.parametrize('claim', [
    '医疗机构或者鉴定机构有明确意见的，可以参照确定护理人数。',
    '能否超过一人并非取决于是否有该意见。',
    '不能说必须取得该意见。',
    '可以参照某意见不等于必须取得该意见。',
    '请整理已有意见。',
])
def test_optional_opinion_and_its_negated_necessity_remain_allowed(claim):
    _, evidence = recorded('E-L-TA-03')
    assert deterministic_rejections(sentence_units(claim), evidence) == []


@pytest.mark.anyio
async def test_exact_server_fact_section_needs_no_model_but_alterations_do():
    _, evidence = recorded('E-L-TA-03')
    assert await checked_paragraph(FACT_RISK, evidence, '材料', NoModel()) == FACT_RISK
    with pytest.raises(AssertionError):
        await validate_grounding(FACT_RISK + '你方必然胜诉。', evidence, '材料', NoModel())


def test_recorded_cross_reference_keeps_assertion_for_audit_without_false_source():
    trace, evidence = recorded('E-L-CD-06')
    original = next(c['output'] for c in trace if c['task'] == 'TASK:COVERAGE')
    with pytest.raises(ModelUnavailableError):
        validate_citations(original, evidence)
    normalized = normalize_cross_references(original, evidence)
    assert normalized == original.replace('民法典第五百八十四条', '该依据援引的条款')
    assert '本轮未提供' in normalized
    validate_citations(normalized, evidence)
    with pytest.raises(ModelUnavailableError):
        validate_citations(normalize_cross_references('依民法典第九千九百条支付。', evidence), evidence)


@pytest.mark.anyio
async def test_normalized_reference_does_not_bypass_semantic_audit():
    _, evidence = recorded('E-L-CD-06')
    class RejectingModel:
        async def complete(self, messages):
            assert 'TASK:GROUNDING' in messages[0].content
            data = json.loads(messages[1].content)
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported'} for u in data['units']]})
    normalized = normalize_cross_references('民法典第五百八十四条保证你免除全部责任。', evidence)
    with pytest.raises(GroundingViolation):
        await validate_grounding(normalized, evidence, '责任', RejectingModel())


def test_optional_rule_does_not_override_another_sources_mandatory_rule():
    _, evidence = recorded('E-L-TA-03')
    source = evidence[0].source.model_copy(update={'citation_id': 'S2'})
    evidence.append(Evidence(source, '申请时必须附相关机构的意见。'))
    assert deterministic_rejections(['申请时必须附相关机构的意见[S2]。'], evidence) == []


@pytest.mark.anyio
async def test_audit_cannot_hide_optional_rule_with_an_unrelated_input_label():
    _, evidence = recorded('E-L-TA-03')
    from tests.agent_helpers import AgentLLM
    class Mislabelled(AgentLLM):
        async def complete(self, messages):
            data = json.loads(messages[1].content)
            if messages[0].content.startswith('TASK:GROUNDING'):
                return json.dumps({'items': [{'unit_id': 0, 'verdict': 'supported',
                    'supports': [{'citation_id': 'S1', 'span_id': 2}]}]})
            return await super().complete(messages)
    with pytest.raises(GroundingViolation) as failure:
        await validate_grounding('只有取得相关意见才能增加护理人数[S4]。', evidence, '人数', Mislabelled())
    assert failure.value.reason == 'unsupported_logic'
