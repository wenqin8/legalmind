import pytest

from app.agents.intent import classify_intent
from app.llm.fake import FakeLLMClient
from app.schemas.chat import ChatRequest
from app.agents.evidence import Evidence, select_evidence, validate_citations
from app.agents.qa import generate_qa
from app.schemas.chat import SourceReference
from uuid import uuid4

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("message,intent,document_type", [
    ("请查找拖欠工资案例", "search", None),
    ("列出交通事故判例", "search", None),
    ("帮我写一份起诉状", "document", "civil_complaint"),
    ("请起草通用合同", "document", "general_contract"),
    ("帮我生成文书", "document", None),
])
async def test_explicit_intent_does_not_need_model(message, intent, document_type):
    llm = FakeLLMClient()
    result = await classify_intent(ChatRequest(message=message), llm)
    assert (result.intent, result.document_type) == (intent, document_type)
    assert llm.call_count == 0


@pytest.mark.parametrize("output", ['bad json', '{"intent":"other"}', '{"intent":"search","confidence":0.2}'])
async def test_invalid_or_uncertain_intent_falls_back(output):
    result = await classify_intent(ChatRequest(message="我该怎么办"), FakeLLMClient(output))
    assert result.intent == "qa"


async def test_explicit_document_type_overrides_message():
    result = await classify_intent(ChatRequest(message="查找案例", document_type="civil_defense"), FakeLLMClient())
    assert result.intent == "document"
    assert result.document_type == "civil_defense"


@pytest.mark.parametrize("message", ["拖欠工资怎么办", "租房押金怎么处理"])
async def test_structured_qa_result(message):
    result = await classify_intent(ChatRequest(message=message), FakeLLMClient('{"intent":"qa","confidence":0.9}'))
    assert result.intent == "qa"


def sample_evidence():
    return [Evidence(SourceReference(source_type="case", source_id=uuid4(), title="工资演示", reference_number="DEMO-LABOR_DISPUTE-001", source_kind="demo", is_demo=True, is_synthetic=True), "演示材料")]


@pytest.mark.parametrize("text", ["根据[S6]", "https://fake.example", "根据第十条", "《虚构法律》", "法院已经判决", "根据[unknown]", "ftp://fake.example", "//fake.example", "fake.gov.cn", "根据［S6］"])
async def test_invalid_source_output_rejected(text):
    from app.core.errors import ModelUnavailableError
    with pytest.raises(ModelUnavailableError):
        validate_citations(text, sample_evidence())


async def test_selection_cannot_invent_ids_or_select_unrelated_sources():
    evidence = sample_evidence()
    for output in ['{"in_scope":true,"source_ids":["' + str(uuid4()) + '"]}', '{"in_scope":false,"source_ids":[]}', 'bad']:
        assert await select_evidence("无关问题", [], evidence, FakeLLMClient(output)) == []


async def test_qa_stream_contains_checked_paragraphs_and_server_sources():
    evidence = sample_evidence()
    result = "".join([part async for part in generate_qa("工资问题", [], evidence, FakeLLMClient("结论\n可整理材料[S1]。\n\n风险\n依据不足。\n\n下一步\n核对记录。", chunk_size=2))])
    assert "工资演示" in result
    assert "DEMO-LABOR_DISPUTE-001" in result
    assert "不是真实判例" in result


async def test_provided_demo_identifier_is_allowed_but_unknown_number_is_not():
    from app.core.errors import ModelUnavailableError
    evidence = sample_evidence()
    validate_citations("演示编号DEMO-LABOR_DISPUTE-001[S1]", evidence)
    validate_citations("请整理《工资材料清单》", evidence)
    with pytest.raises(ModelUnavailableError):
        validate_citations("DEMO-LABOR_DISPUTE-999", evidence)


async def test_old_citation_labels_are_not_current_evidence():
    from datetime import datetime, timezone
    from app.agents.evidence import model_history
    from app.schemas.chat import ConversationMessage
    history = [ConversationMessage(role="assistant", content="旧结论[S1]\n\n参考材料\n旧来源", created_at=datetime.now(timezone.utc))]
    assert "旧来源" not in model_history(history)[0]["content"]
    assert "[S1]" not in model_history(history)[0]["content"]


async def test_split_forbidden_identifier_is_rejected_before_closing_paragraph():
    from app.core.errors import ModelUnavailableError
    delivered = []
    llm = FakeLLMClient("结论\n材料[S1]。\n\nhttp\n\ns://fake.example\n\n风险\n下一步", chunk_size=2)
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa("工资问题", [], sample_evidence(), llm):
            delivered.append(part)
    assert "fake.example" not in "".join(delivered)


async def test_open_citation_is_not_streamed_as_a_complete_paragraph():
    from app.core.errors import ModelUnavailableError
    delivered = []
    llm = FakeLLMClient('结论\n未知引用[S9\n\n]。\n\n风险\n下一步',chunk_size=2)
    with pytest.raises(ModelUnavailableError):
        async for part in generate_qa('工资问题',[],sample_evidence(),llm):
            delivered.append(part)
    assert not delivered
