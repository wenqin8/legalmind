import json
from uuid import uuid4

import pytest

from app.agents.evidence import Evidence
from app.agents.grounding import validate_grounding
from app.agents.qa import generate_qa
from app.core.errors import ModelUnavailableError
from app.llm.fake import FakeLLMClient
from app.schemas.chat import SourceReference

pytestmark = pytest.mark.anyio


class CheckedFake(FakeLLMClient):
    async def complete(self, messages):
        if messages[0].content.startswith('TASK:CONDITIONS'):
            data = json.loads(messages[1].content)
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'consistent'} for u in data['units']]})
        return await super().complete(messages)


def evidence():
    text = '申请人应当提供证明材料。'
    source = SourceReference(source_type='legal_provision', source_id=uuid4(), title='测试条文',
        reference_number='第一条', source_kind='official', is_demo=False, version='测试版',
        original_text=text, effective_from='2025-01-01', verified_at='2026-09-01',
        status_as_of='2026-09-01', source_url='https://www.court.gov.cn/test', applicability='general_reference')
    return [Evidence(source, text)]


@pytest.mark.parametrize('items', [
    [],
    [{'unit_id': 0, 'verdict': 'unsupported', 'supports': []}],
    [{'unit_id': 0, 'verdict': 'neutral', 'supports': []}],
    [{'unit_id': 0, 'verdict': 'supported', 'supports': []}],
    [{'unit_id': 0, 'verdict': 'supported', 'supports': [{'citation_id': 'S1', 'quote': '不在原文中的条件'}]}],
    [{'unit_id': 0, 'verdict': 'supported', 'supports': [{'citation_id': 'S4', 'quote': '申请人应当提供证明材料。'}]}],
])
async def test_checker_cannot_omit_claims_or_fabricate_support(items):
    with pytest.raises(ModelUnavailableError):
        await validate_grounding('结论\n申请人需要提供证明材料[S1]。', evidence(), '需要哪些材料',
                                 FakeLLMClient(json.dumps({'items': items})))


async def test_valid_support_is_rendered_with_its_own_citation():
    raw = json.dumps({'items': [{'unit_id': 0, 'verdict': 'supported', 'supports': [
        {'citation_id': 'S1', 'quote': '申请人应当提供证明材料。'}]}]})
    await validate_grounding('结论\n申请人需要提供证明材料[S1]。', evidence(), '材料', CheckedFake(raw))
    result = await validate_grounding('结论\n申请人需要提供证明材料。', evidence(), '材料', CheckedFake(raw))
    assert result == '结论\n[S1] 申请人需要提供证明材料。'


async def test_server_added_label_does_not_turn_a_quoted_term_into_a_verbatim_quote():
    from app.agents.evidence import validate_citations
    raw = json.dumps({'items': [{'unit_id': 0, 'verdict': 'supported', 'supports': [
        {'citation_id': 'S1', 'quote': '申请人应当提供证明材料。'}]}]})
    result = await validate_grounding('结论\n需要提供“证明材料”。', evidence(), '材料', CheckedFake(raw))
    validate_citations(result, evidence())


async def test_unsupported_paragraph_is_rejected_before_emission():
    class RejectedLLM(FakeLLMClient):
        async def complete(self, messages):
            data = json.loads(messages[1].content)
            if messages[0].content.startswith('TASK:REVISE'):
                return data['paragraph']
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported', 'supports': []}
                                         for u in data['units']]})
    delivered = []
    model = RejectedLLM('结论\n可以免除全部付款义务[S1]。\n\n风险\n核对。\n\n下一步\n核对。', chunk_size=2)
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa('能否免除付款', [], evidence(), model):
            delivered.append(part)
    assert not delivered


def test_support_layout_lookup_returns_original_not_model_rewritten_text():
    from app.agents.support_spans import exact_support
    assert exact_support('第一条\u00a0 应当提供材料。', '第一条  应当提供材料。') == '第一条\u00a0 应当提供材料。'
    assert exact_support('不应当支持返还。', '应当支持返还。') == '应当支持返还。'  # substring alone is not entailment
    assert exact_support('应当提供材料。', '无需提供材料。') is None


@pytest.mark.parametrize('items', [[], [{'unit_id': 0, 'verdict': 'unsupported', 'explanation': '遗漏法定前提'}]])
async def test_condition_check_can_block_a_first_reviewer_approval(items):
    class ConditionRejector(CheckedFake):
        async def complete(self, messages):
            if messages[0].content.startswith('TASK:CONDITIONS'):
                return json.dumps({'items': items})
            return await super().complete(messages)
    raw = json.dumps({'items': [{'unit_id': 0, 'verdict': 'supported', 'supports': [
        {'citation_id': 'S1', 'quote': '申请人应当提供证明材料。'}]}]})
    with pytest.raises(ModelUnavailableError):
        await validate_grounding('结论\n申请人应当提供材料。', evidence(), '材料', ConditionRejector(raw))
