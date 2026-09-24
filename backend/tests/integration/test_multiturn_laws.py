import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.core.errors import DatabaseUnavailableError
from app.db.models import GeneratedDocument
from app.rag.legal_catalog import import_catalog, load_catalog
from app.services.session_store import HistorySnapshot
from tests.agent_helpers import AgentLLM, configure_agent
from tests.integration.test_chat import auth, send

pytestmark = pytest.mark.anyio


class ScriptedLLM(AgentLLM):
    """Extraction grounded in explicitly labelled synthetic user messages."""
    def __init__(self):
        super().__init__()
        self.domain = 'labor_dispute'
        self.applicability_ids = None
        self.missing = []
        self.response = '结论\n可在核对适用前提后参考所附条文[S1]。\n\n风险\n主体、时间和例外尚须结合证据核实。\n\n下一步\n整理已有书面材料。'

    async def complete(self, messages):
        if 'TASK:EXTRACT' in messages[0].content:
            data = json.loads(messages[1].content)
            fields = []
            for part in data['message'].split('；'):
                name, sep, value = part.partition('=')
                if sep and name in data['allowed_fields']:
                    fields.append({'name':name,'value':value,'quote':part})
            return json.dumps({'domain':self.domain,'general_question':False,'fields':fields}, ensure_ascii=False)
        if 'TASK:APPLICABILITY' in messages[0].content:
            data = json.loads(messages[1].content)
            first = data['candidates'][0]
            return json.dumps({'assessment':'conditional','source_ids':self.applicability_ids if self.applicability_ids is not None else [first['source_id']],
                               'missing_fields':self.missing, 'direct_support': {first['source_id']:first['source']['original_text']}})
        return await super().complete(messages)


@pytest.fixture(autouse=True)
def setup(app):
    configure_agent(app)
    import_catalog(app.state.database, load_catalog(Path('data/legal/verified_provisions.jsonl')))
    app.state.llm_client = ScriptedLLM()


@pytest.mark.parametrize('domain,facts,context', [
    ('labor_dispute','公司拖欠工资','劳动合同和工资转账记录'),
    ('marriage_family','离婚后孩子抚养费争议','婚姻关系和子女情况有材料'),
    ('traffic_accident','机动车撞到行人要求赔偿','有事故认定书和医疗记录'),
    ('contract_dispute','对方不履行合同构成违约','有合同和付款记录'),
])
async def test_qa_clarifies_then_returns_versioned_official_sources(client, app, domain, facts, context):
    app.state.llm_client.domain = domain
    headers = await auth(client)
    first = (await send(client, headers, message='facts='+facts)).json()['data']
    assert first['sources'] == [] and 'event_date' in first['missing_fields']
    second = await send(client, headers, session_id=first['session_id'], message=f'event_date=2025年6月1日；context={context}')
    assert second.status_code == 200
    data = second.json()['data']
    assert data['task']['phase'] == 'completed'
    assert data['sources'] and all(s['source_type'] == 'legal_provision' for s in data['sources'])
    source = data['sources'][0]
    assert source['original_text'] in data['response']
    assert source['verified_at'] == '2026-09-18'
    assert source['version'] and source['applicability'] == 'event_candidate'
    assert data['task']['fields']['facts']['source_turn_id'] == first['task']['fields']['facts']['source_turn_id']


async def test_review_state_survives_trimming_then_confirmation_is_atomic(client, app, monkeypatch):
    headers = await auth(client)
    first = (await send(client, headers, message='原告=甲', document_type='civil_complaint', document_params={'plaintiff':'合成甲'})).json()['data']
    sid = first['session_id']
    for _ in range(11):
        assert (await send(client, headers, message='继续补充', session_id=sid)).status_code == 200
    params = {'defendant':'合成乙','claims':'返还合成款项','facts_and_reasons':'合成场景：付款未交货','court':'测试法院（未提交）'}
    review = (await send(client, headers, message='补齐', session_id=sid, document_params=params)).json()['data']
    assert review['task']['phase'] == 'review'
    assert review['task']['fields']['plaintiff']['source_turn_id'] == first['task']['fields']['plaintiff']['source_turn_id']
    before = dict(app.state.session_store.rows)
    def fail(*args): raise DatabaseUnavailableError()
    with monkeypatch.context() as patch:
        patch.setattr('app.services.chat.save_completion', fail)
        result = await send(client, headers, message='确认生成', session_id=sid)
        assert result.status_code == 503
    assert app.state.session_store.rows == before
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(GeneratedDocument)) == 0
    result = await send(client, headers, message='确认生成', session_id=sid, task_revision=review['task']['revision'])
    assert result.status_code == 200 and result.json()['data']['document_id']
    doc_id = result.json()['data']['document_id']
    repeated = (await send(client, headers, message='确认生成', session_id=sid)).json()['data']
    assert repeated['document_id'] == doc_id
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(GeneratedDocument)) == 1


async def test_expired_tasks_and_stale_confirmation_never_generate(client, app):
    headers = await auth(client)
    first = (await send(client, headers, document_type='general_contract', document_params={'party_a':'合成甲'})).json()['data']
    key = next(iter(app.state.session_store.rows))
    old = app.state.session_store.rows[key]
    app.state.session_store.rows[key] = HistorySnapshot(old.messages, time.monotonic()-1)
    for path in ('send','stream'):
        stale = await send(client, headers, message='确认生成', session_id=first['session_id'], task_revision=first['task']['revision'], path=path)
        assert stale.status_code == 409 and stale.json()['error']['code'] == 'TASK_CHANGED'
    new = (await send(client, headers, message='继续', session_id=first['session_id'], document_type='general_contract')).json()['data']
    assert new['task']['fields'] == {} and 'party_a' in new['missing_fields']
    assert any('过期' in x for x in new['warnings'])


@pytest.mark.parametrize('bad_output', ['结论\n未知[S5]。', '结论\n“条文被篡改”[S1]。', '结论\nhttps://fake.example.cn', '结论\n依据第九千条'])
async def test_failed_legal_generation_does_not_advance_task_or_history(client, app, bad_output):
    headers = await auth(client)
    first = (await send(client, headers, message='facts=公司拖欠工资')).json()['data']
    before = dict(app.state.session_store.rows)
    app.state.llm_client.response = bad_output + '\n\n风险\n风险。\n\n下一步\n下一步。'
    result = await send(client, headers, session_id=first['session_id'], message='event_date=2025年6月1日；context=有劳动合同')
    assert result.status_code == 424
    assert app.state.session_store.rows == before


async def test_unknown_applicability_source_fails_closed(client, app):
    headers = await auth(client)
    app.state.llm_client.applicability_ids = [str(uuid4())]
    result = await send(client, headers, message='facts=公司拖欠工资；event_date=2025年6月1日；context=有合同')
    assert result.status_code == 424
    assert result.json()['error']['code'] == 'MODEL_UNAVAILABLE'


async def test_exact_legal_quotation_and_statutory_procedure_are_distinct_from_fabricated_judgment(app):
    from app.agents.legal_evidence import legal_evidence
    from app.agents.evidence import validate_citations
    from app.schemas.tasks import TaskState
    from app.core.errors import ModelUnavailableError
    task = TaskState(kind='qa', domain='marriage_family', mode='general')
    evidence = (await legal_evidence(app.state.database,'子女抚养费',task,app.state.llm_client)).evidence
    assert evidence
    source = evidence[0].source
    if '人民法院判决' not in source.original_text:
        # Select the relevant provision explicitly for this validation test.
        from app.schemas.chat import SourceReference
        from app.agents.evidence import Evidence
        source = source.model_copy(update={'original_text':'协议不成时，由人民法院判决。'})
        evidence = [Evidence(source,source.original_text)]
    label = source.citation_id
    validate_citations(f'一般规则中协议不成可由人民法院判决[{label}]。',evidence)
    validate_citations(f'“{source.original_text}”[{label}]',evidence)
    validate_citations(f'请整理“相关材料”，注意适用前提[{label}]。',evidence)
    for text in (f'法院已经判决[{label}]',f'原文：“伪造内容”[{label}]',f'原文：“伪造内容”'):
        with pytest.raises(ModelUnavailableError):
            validate_citations(text,evidence)
