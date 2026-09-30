"""Replay the real run17 omitted refund prerequisite without model calls."""

import json
from pathlib import Path

import pytest

from app.agents.claim_rules import deterministic_rejections
from app.agents.evidence import Evidence
from app.agents.grounding import GroundingViolation, sentence_units, validate_grounding
from app.schemas.chat import SourceReference


def archived_refund():
    path = Path(__file__).resolve().parents[3] / 'docs/acceptance/rag-v2-targeted-run17.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    turn = next(s for s in raw['scenarios'] if s['id'] == 'E-L-LD-01')['turns'][0]
    response = turn['response']
    return response['response'].split('\n\n风险\n')[0], [
        Evidence(SourceReference.model_validate(s), s['original_text']) for s in response['sources']]


@pytest.mark.anyio
async def test_recorded_refund_without_linked_prerequisite_is_rejected():
    paragraph, evidence = archived_refund()
    class NoModel:
        async def complete(self, messages):
            raise AssertionError('Missing prerequisite must be rejected before model review')
    with pytest.raises(GroundingViolation) as failure:
        await validate_grounding(paragraph, evidence, '补缴后社保补偿返还', NoModel())
    assert failure.value.reason == 'unsupported_logic'
    assert len(failure.value.feedback) == 1
    assert '返还' in failure.value.feedback[0]['text']


@pytest.mark.parametrize('claim', [
    '有前款规定情形，用人单位依法补缴社会保险费后，请求劳动者返还已支付的社会保险费补偿的，依法予以支持[S1]。',
    '在上述约定无效及未依法缴费解除劳动合同的情形下，依法补缴后请求返还已付社保补偿的，依法支持[S1]。',
    '不能仅凭补缴社会保险费就认定有权返还已支付的社会保险费补偿[S1]。',
    '是否可以返还社保补偿，本次不作判断[S1]。',
])
def test_explicit_link_or_nonconclusion_does_not_trigger_guard(claim):
    _, evidence = archived_refund()
    assert deterministic_rejections(sentence_units(claim), evidence) == []


def test_prerequisite_word_elsewhere_cannot_mask_unconditional_refund():
    _, evidence = archived_refund()
    paragraph = '有前款规定情形应核实。用人单位依法补缴后请求返还社保补偿的，依法支持[S1]。'
    assert len(deterministic_rejections(sentence_units(paragraph), evidence)) == 1


def test_other_source_refund_rule_is_not_overridden():
    _, evidence = archived_refund()
    source = evidence[0].source.model_copy(update={'citation_id': 'S2'})
    evidence.append(Evidence(source, '测试规则：多付的补偿款可以请求返还。'))
    assert deterministic_rejections(['可以请求返还多付补偿款[S2]。'], evidence) == []
