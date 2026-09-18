import json
from uuid import uuid4

import pytest

from app.agents.tasks import advance_task
from app.schemas.chat import ChatRequest
from app.schemas.tasks import TaskState, GroundedValue
from app.schemas.documents import TEMPLATES
from app.core.errors import AppError
from tests.agent_helpers import AgentLLM

pytestmark = pytest.mark.anyio


class ExtractLLM(AgentLLM):
    def __init__(self, fields=None, domain=None, general=False):
        super().__init__()
        self.fields = fields or []
        self.domain = domain
        self.general = general

    async def complete(self, messages):
        if 'TASK:EXTRACT' in messages[0].content:
            return json.dumps({'fields': self.fields, 'domain': self.domain, 'general_question': self.general}, ensure_ascii=False)
        return await super().complete(messages)


@pytest.mark.parametrize('kind', list(TEMPLATES))
async def test_document_collect_review_conflict_confirm_cancel(kind):
    fields = TEMPLATES[kind].fields
    turn = uuid4()
    task, authorized = await advance_task(ChatRequest(message='开始', document_type=kind), None, kind='document', turn_id=turn, llm=ExtractLLM())
    assert task.phase == 'collecting' and 1 <= len(task.questions) <= 3 and not authorized
    params = {f.name: f'用户填写的{f.label}' for f in fields}
    task, authorized = await advance_task(ChatRequest(message='补齐', document_params=params), task, kind='document', turn_id=turn, llm=ExtractLLM())
    assert task.phase == 'review' and not authorized
    original = task.model_copy(deep=True)
    first = fields[0].name
    revised, authorized = await advance_task(ChatRequest(message='更正', document_params={first:'新值'}), task, kind='document', turn_id=uuid4(), llm=ExtractLLM())
    assert revised.phase == 'conflict' and revised.fields[first].value == params[first]
    assert revised.conflicts[first].value == '新值'
    assert original == task  # caller state was not mutated
    reviewed, authorized = await advance_task(ChatRequest(message='确认修改'), revised, kind='document', turn_id=uuid4(), llm=ExtractLLM())
    assert reviewed.phase == 'review' and reviewed.fields[first].value == '新值' and not authorized
    with pytest.raises(AppError) as error:
        await advance_task(ChatRequest(message='确认生成', task_revision=original.revision), reviewed, kind='document', turn_id=uuid4(), llm=ExtractLLM())
    assert error.value.code == 'TASK_CHANGED'
    completed, authorized = await advance_task(ChatRequest(message='确认生成', task_revision=reviewed.revision), reviewed, kind='document', turn_id=uuid4(), llm=ExtractLLM())
    assert authorized and completed.phase == 'completed'
    cancelled, authorized = await advance_task(ChatRequest(message='取消'), reviewed, kind='document', turn_id=uuid4(), llm=ExtractLLM())
    assert cancelled.phase == 'cancelled' and not cancelled.fields and not authorized


async def test_extraction_rejects_ungrounded_values_and_tracks_source_message():
    llm = ExtractLLM([
        {'name':'plaintiff','value':'张三','quote':'原告是张三'},
        {'name':'defendant','value':'李四','quote':'原告是张三'},
        {'name':'claims','value':'一百万元','quote':'请判一百万元'},
        {'name':'admin','value':'张三','quote':'张三'},
    ])
    turn = uuid4()
    task, _ = await advance_task(ChatRequest(message='原告是张三', document_type='civil_complaint'), None, kind='document', turn_id=turn, llm=llm)
    assert list(task.fields) == ['plaintiff']
    assert task.fields['plaintiff'].source_turn_id == turn
    assert task.fields['plaintiff'].quote == '原告是张三'


@pytest.mark.parametrize('domain', ['marriage_family','labor_dispute','traffic_accident','contract_dispute'])
async def test_qa_requires_material_event_date_and_context(domain):
    llm = ExtractLLM([{'name':'facts','value':'发生纠纷','quote':'发生纠纷'}], domain)
    task, _ = await advance_task(ChatRequest(message='发生纠纷'), None, kind='qa', turn_id=uuid4(), llm=llm)
    assert task.phase == 'collecting' and 'event_date' in task.missing_fields
    assert len(task.questions) <= 3
    llm.fields = [{'name':'event_date','value':'2025年6月1日','quote':'2025年6月1日'}, {'name':'context','value':'已有书面材料','quote':'已有书面材料'}]
    ready, _ = await advance_task(ChatRequest(message='2025年6月1日，已有书面材料'), task, kind='qa', turn_id=uuid4(), llm=llm)
    assert ready.phase == 'completed' and ready.fields['facts'].value == '发生纠纷'
    llm.fields = [{'name':'event_date','value':'2020年','quote':'2020年'}]
    conflict, _ = await advance_task(ChatRequest(message='更正为2020年'), ready, kind='qa', turn_id=uuid4(), llm=llm)
    assert conflict.phase == 'conflict' and conflict.fields['event_date'].value == '2025年6月1日'


async def test_switch_domain_does_not_reuse_previous_facts():
    prior = TaskState(kind='qa', domain='labor_dispute', fields={'event_date':GroundedValue(value='2025年',quote='2025年',source_turn_id=uuid4())})
    new, _ = await advance_task(ChatRequest(message='现在询问离婚'), prior, kind='qa', turn_id=uuid4(), llm=ExtractLLM(domain='marriage_family'))
    assert new.task_id != prior.task_id and new.fields == {}


@pytest.mark.parametrize('message,domain', [('了解离婚子女抚养的一般规定','marriage_family'),('了解劳动合同的一般规定','labor_dispute'),('了解机动车保险一般规定','traffic_accident'),('了解普通合同违约一般规定','contract_dispute')])
async def test_general_questions_have_a_domain_without_invented_event_dates(message, domain):
    task, _ = await advance_task(ChatRequest(message=message), None, kind='qa', turn_id=uuid4(), llm=ExtractLLM(general=True))
    assert task.domain == domain and task.mode == 'general'
    assert not task.fields and task.phase == 'completed'


async def test_completed_document_can_be_corrected_without_rewriting_old_draft():
    values = {f.name: GroundedValue(value=f.label,quote=f.label,source_turn_id=uuid4()) for f in TEMPLATES['civil_complaint'].fields}
    old_id = uuid4()
    task = TaskState(kind='document',document_type='civil_complaint',phase='completed',fields=values,document_id=old_id)
    changed, ready = await advance_task(ChatRequest(message='更正法院',document_params={'court':'新测试法院'}),task,kind='document',turn_id=uuid4(),llm=ExtractLLM())
    assert changed.phase == 'conflict' and changed.document_id is None and not ready
    assert task.document_id == old_id
    reviewed, ready = await advance_task(ChatRequest(message='确认修改'),changed,kind='document',turn_id=uuid4(),llm=ExtractLLM())
    assert reviewed.phase == 'review' and not ready


async def test_unspecified_template_prompts_without_accepting_unknown_parameters():
    task, ready = await advance_task(ChatRequest(message='帮我生成文书',document_params={'unknown':'x'}),None,kind='document',turn_id=uuid4(),llm=ExtractLLM())
    assert task.missing_fields == ['document_type'] and not task.fields and not ready
