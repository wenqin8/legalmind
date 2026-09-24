import json

import pytest

from app.agents.qa import generate_qa
from app.core.errors import ModelUnavailableError
from app.llm.fake import FakeLLMClient
from tests.unit.test_grounding import evidence

pytestmark = pytest.mark.anyio


class ContextReviewer(FakeLLMClient):
    def __init__(self, response, revision='结论\n申请人应当提供证明材料[S1]。'):
        super().__init__(response, chunk_size=2)
        self.calls = []
        self.revision = revision

    async def complete(self, messages):
        task = messages[0].content.split('\n')[0]
        data = json.loads(messages[1].content)
        self.calls.append((task, data))
        if task == 'TASK:REVISE':
            return self.revision
        items = []
        for unit in data['units']:
            if task == 'TASK:CONDITIONS':
                items.append({'unit_id': unit['unit_id'], 'verdict': 'consistent'})
            else:
                items.append({'unit_id': unit['unit_id'], 'verdict': 'supported',
                              'supports': [{'citation_id': 'S1', 'span_id': 0}]})
        return json.dumps({'items': items})


async def test_reviewers_receive_whole_paragraph_and_only_validated_prior_context():
    model = ContextReviewer('结论\n申请人应当提供证明材料[S1]。\n\n风险\n核对前述材料。\n\n下一步\n最后整理。')
    parts = [part async for part in generate_qa('材料', [], evidence(), model)]
    for task, data in model.calls:
        assert data['paragraph']
        if data['paragraph'].startswith('结论'):
            assert data['validated_context'] == ''
            assert '最后整理' not in json.dumps(data, ensure_ascii=False)
        elif data['paragraph'].startswith('风险'):
            assert data['validated_context'] == parts[0]
            assert '最后整理' not in json.dumps(data, ensure_ascii=False)
    assert '参考材料' in parts[-1]


async def test_unprovided_cross_reference_is_repaired_and_raw_text_never_emitted():
    model = ContextReviewer('结论\n依照第一百五十七条处理[S1]。\n\n风险\n核对材料。\n\n下一步\n整理材料。')
    parts = [part async for part in generate_qa('材料', [], evidence(), model)]
    assert '第一百五十七条' not in ''.join(parts)
    revisions = [data for task, data in model.calls if task == 'TASK:REVISE']
    assert len(revisions) == 1
    assert revisions[0]['failure'] == 'invalid_citation'
    later = [data for task, data in model.calls if task == 'TASK:GROUNDING' and data['paragraph'].startswith('风险')]
    assert later[0]['validated_context'] == parts[0]
    assert '第一百五十七条' not in later[0]['validated_context']


async def test_failed_format_revision_is_never_sent_and_has_no_retry_loop():
    model = ContextReviewer('结论\n依照第一百五十七条处理[S1]。\n\n', revision='结论\n依照第九百条处理[S1]。')
    parts = []
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa('材料', [], evidence(), model):
            parts.append(part)
    assert not parts
    assert sum(task == 'TASK:REVISE' for task, _ in model.calls) == 1


async def test_split_identifier_still_checked_against_delivered_prefix():
    model = ContextReviewer('结论\n申请人应当提供证明材料[S1]。第九百\n\n条另有规定。\n\n风险\n核对。\n\n下一步\n核对。', revision='条另有规定。')
    parts = []
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa('材料', [], evidence(), model):
            parts.append(part)
    assert len(parts) == 1
    assert '条另有规定' not in parts[0]


async def test_format_and_semantic_failures_share_one_revision_budget():
    class SemanticRejector(ContextReviewer):
        async def complete(self, messages):
            if messages[0].content.startswith('TASK:GROUNDING'):
                data = json.loads(messages[1].content)
                return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported'} for u in data['units']]})
            return await super().complete(messages)
    model = SemanticRejector('结论\n依照第一百五十七条处理[S1]。\n\n')
    with pytest.raises(ModelUnavailableError):
        _ = [part async for part in generate_qa('材料', [], evidence(), model)]
    assert sum(task == 'TASK:REVISE' for task, _ in model.calls) == 1


def test_audit_context_drops_whole_earliest_paragraph_without_partial_conditions():
    from app.agents.qa import audit_context
    first = '先前条件' * 2990 + '\n\n'
    second = '只有满足条件才可以适用。\n\n' * 5
    assert audit_context(first + second) == second
