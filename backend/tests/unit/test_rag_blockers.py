"""Regression tests for the pre-fix RAG failure mechanisms, using synthetic data."""

import json
from uuid import uuid4

import pytest

from app.agents.evidence import Evidence, validate_citations
from app.agents.workflow import build_workflow
from app.evaluation.dataset import catalog_entries
from app.llm.fake import FakeLLMClient
from app.rag.legal_catalog import import_catalog, retrieve_provisions
from app.schemas.chat import ChatRequest, SourceReference
from app.schemas.tasks import GroundedValue, TaskState

pytestmark = pytest.mark.anyio


def test_evaluation_login_is_not_skipped_after_machine_boot():
    from scripts.evaluate_rag_answers import needs_login
    assert needs_login(None, 0, 100)
    assert not needs_login('synthetic-token', 100, 101)
    assert needs_login('synthetic-token', 100, 2501)


class WrongIntentLLM(FakeLLMClient):
    async def complete(self, messages):
        if messages[0].content.startswith('TASK:EXTRACT'):
            data = json.loads(messages[1].content)
            return json.dumps({'domain': data['domain'], 'general_question': False, 'fields': [
                {'name': 'event_date', 'value': '2026年8月2日', 'quote': data['message']} ]}, ensure_ascii=False)
        return '{"intent":"document","confidence":0.99,"document_type":null}'


@pytest.mark.parametrize('domain', ['marriage_family', 'labor_dispute', 'traffic_accident', 'contract_dispute'])
async def test_qa_correction_is_routed_before_incorrect_model_classification(app, domain):
    old = GroundedValue(value='2026年7月2日', quote='2026年7月2日', source_turn_id=uuid4())
    task = TaskState(kind='qa', domain=domain, phase='completed', fields={'event_date': old})
    graph = build_workflow(app.state.database, None, WrongIntentLLM())
    base = {'request_id': uuid4(), 'user_id': uuid4(), 'session_id': uuid4(),
            'conversation_messages': [], 'warnings': [], 'task': task}
    state = await graph.ainvoke({**base, 'payload': ChatRequest(message='更正事件日期：2026年8月2日。')})
    result = state['result']
    assert result.intent == 'qa' and result.task.task_id == task.task_id
    assert result.task.phase == 'conflict' and result.task.fields['event_date'] == old
    assert result.task.conflicts['event_date'].value == '2026年8月2日'
    accepted = await graph.ainvoke({**base, 'task': result.task, 'payload': ChatRequest(message='确认修改')})
    assert accepted['result'].task.fields['event_date'].value == '2026年8月2日'
    assert accepted['result'].task.task_id == task.task_id


@pytest.mark.parametrize('query,domain,target', [
    ('单位自愿不交社保的承诺，补缴后社保补偿怎么办', 'labor_dispute', 'labor_ii-2025-07-31-19'),
    ('雇护工时护理人数和费用需要哪些证据', 'traffic_accident', 'personal_injury-2022-04-24-8'),
])
async def test_relevant_bm25_hit_is_not_deleted_by_literal_keyword_gate(app, query, domain, target):
    import_catalog(app.state.database, catalog_entries())
    rows = retrieve_provisions(app.state.database, query, domain, event_date=None, general=True)
    assert target in [r.record_id for r, _ in rows]


async def test_negative_statement_with_term_quotes_is_not_a_statutory_quote():
    source = SourceReference(source_type='legal_provision', source_id=uuid4(), title='测试法规',
        reference_number='第一条', source_kind='official', is_demo=False, version='测试版',
        original_text='应当提供材料。', effective_from='2025-01-01', verified_at='2026-09-01',
        status_as_of='2026-09-01', source_url='https://www.court.gov.cn/test', applicability='general_reference')
    validate_citations('材料未规定“某项返还”的具体条件，依据不足[S1]。', [Evidence(source, source.original_text)])


async def test_empty_extraction_does_not_discard_explicit_legal_domain(app):
    from pathlib import Path
    report = json.loads((Path(__file__).resolve().parents[3] /
        'docs/acceptance/rag-v2-development-answers-run19.json').read_text(encoding='utf-8'))
    turn = next(s for s in report['scenarios'] if s['id'] == 'E-L-CD-14')['turns'][0]
    extraction = next(c for c in turn['model_trace'] if c['task'] == 'TASK:EXTRACT')
    class Replay(FakeLLMClient):
        async def complete(self, messages):
            if messages[0].content.startswith('TASK:INTENT'):
                return '{"intent":"qa","confidence":1.0,"document_type":null}'
            assert messages[0].content.startswith('TASK:EXTRACT')
            return extraction['output']
    graph = build_workflow(app.state.database, None, Replay())
    state = await graph.ainvoke({'request_id': uuid4(), 'user_id': uuid4(), 'session_id': uuid4(),
        'conversation_messages': [], 'warnings': [],
        'payload': ChatRequest(message=turn['expected']['message'])})
    assert state['result'].task.domain == 'contract_dispute'
    assert state['result'].task.phase == 'collecting'
    assert state['result'].sources == []
