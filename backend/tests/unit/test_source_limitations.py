import json
from pathlib import Path

import pytest

from app.agents.evidence import Evidence, validate_citations
from app.agents.limitations import omitted_limitation_notice
from app.core.errors import ModelUnavailableError
from app.schemas.chat import SourceReference


def archived():
    root = Path(__file__).resolve().parents[3]
    raw = json.loads((root / 'docs/acceptance/rag-v2-development-answers-run14.json').read_text(encoding='utf-8'))
    data = next(s for s in raw['scenarios'] if s['id'] == 'E-L-CD-06')['turns'][0]['response']
    body = data['response'].split('\n\n参考材料\n')[0]
    return body, [Evidence(SourceReference.model_validate(s), s['original_text']) for s in data['sources']]


def test_recorded_omission_gets_exact_limitation_without_model_or_new_source():
    body, evidence = archived()
    assert '恶意违约' not in body
    notice = omitted_limitation_notice(body, evidence)
    quote = '恶意违约的当事人一方请求减少违约金的，人民法院一般不予支持。'
    assert quote in notice and quote in evidence[0].source.original_text
    assert '[S1]' in notice
    assert omitted_limitation_notice(body + notice, evidence) == ''
    validate_citations(body + notice, evidence)


def test_unrelated_question_or_missing_original_does_not_invent_limitation():
    body, evidence = archived()
    assert omitted_limitation_notice('请问如何确认合同成立？', evidence) == ''
    assert omitted_limitation_notice(body, []) == ''
    source = evidence[0].source.model_copy(update={'original_text': '不匹配的其他版本'})
    with pytest.raises(ModelUnavailableError):
        omitted_limitation_notice(body, [Evidence(source, evidence[0].text)])


@pytest.mark.anyio
@pytest.mark.parametrize('reject_primary', [False, True])
async def test_generator_preserves_limitation_only_after_primary_answer_passes(reject_primary):
    from app.agents.qa import generate_qa
    from tests.agent_helpers import AgentLLM
    body, evidence = archived()
    class Model(AgentLLM):
        async def complete(self, messages):
            if reject_primary and messages[0].content.startswith('TASK:GROUNDING'):
                data = json.loads(messages[1].content)
                return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'unsupported'} for u in data['units']]})
            return await super().complete(messages)
    model = Model()
    model.response = body
    parts = []
    async def collect():
        async for part in generate_qa('违约金减少标准', [], evidence, model):
            parts.append(part)
    if reject_primary:
        with pytest.raises(ModelUnavailableError):
            await collect()
        assert not parts
    else:
        await collect()
        assert '风险补充' in parts[-2] and '恶意违约' in parts[-2]
        assert '参考材料' in parts[-1]
        assert not any(call[0].content.startswith('TASK:COVERAGE') for call in model.requests)
