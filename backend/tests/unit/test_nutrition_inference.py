"""A reference rule does not establish that evidence is unnecessary."""

import json
from pathlib import Path

import pytest

from app.agents.claim_rules import deterministic_rejections
from app.agents.evidence import Evidence
from app.agents.grounding import GroundingViolation, sentence_units, validate_grounding
from app.schemas.chat import SourceReference


def archived_nutrition():
    path = Path(__file__).resolve().parents[3] / 'docs/acceptance/rag-v2-development-answers-run19.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    response = next(s for s in raw['scenarios'] if s['id'] == 'E-L-TA-05')['turns'][1]['response']
    paragraph = response['response'].split('\n\n')[1]
    return paragraph, [Evidence(SourceReference.model_validate(s), s['original_text']) for s in response['sources']]


@pytest.mark.anyio
async def test_recorded_unnecessary_evidence_inference_is_rejected():
    paragraph, evidence = archived_nutrition()
    class NoModel:
        async def complete(self, messages):
            raise AssertionError('Reject unsupported negative inference before model review')
    with pytest.raises(GroundingViolation) as failure:
        await validate_grounding(paragraph, evidence, '营养费意见的作用', NoModel())
    assert failure.value.reason == 'unsupported_logic'


@pytest.mark.parametrize('claim', [
    '营养费根据伤残情况参照医疗机构的意见确定[S1]。',
    '原文仅说明参照意见，不能据此认定医疗机构意见不是必要条件[S1]。',
    '是否需要该意见以外的证明材料，本次不作判断[S1]。',
])
def test_reference_rule_and_explicit_uncertainty_remain_allowed(claim):
    _, evidence = archived_nutrition()
    assert deterministic_rejections(sentence_units(claim), evidence) == []


@pytest.mark.parametrize('claim', [
    '无需取得医疗机构意见也能获得营养费[S1]。',
    '医疗机构意见不是赔偿的必要条件[S1]。',
])
def test_negative_requirement_needs_its_own_evidence(claim):
    _, evidence = archived_nutrition()
    assert deterministic_rejections(sentence_units(claim), evidence)


def test_reference_rule_does_not_establish_an_opposite_mandatory_requirement():
    _, evidence = archived_nutrition()
    claim = '医疗机构意见的作用是作为确定营养费的参照依据，而非可有可无的材料[S1]。'
    assert deterministic_rejections(sentence_units(claim), evidence)


def test_rule_does_not_override_another_selected_source():
    _, evidence = archived_nutrition()
    other = evidence[0].source.model_copy(update={'citation_id': 'S2'})
    evidence.append(Evidence(other, '测试规则：无需提供有关机构意见。'))
    assert deterministic_rejections(['无需提供有关机构意见[S2]。'], evidence) == []
