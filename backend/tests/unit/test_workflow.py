from uuid import uuid4

import pytest

from app.agents.workflow import build_workflow
from app.schemas.chat import ChatRequest
from tests.agent_helpers import AgentLLM

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("message,document_type,intent", [
    ("拖欠工资怎么办", None, "qa"), ("租房纠纷如何处理", None, "qa"),
    ("查找拖欠工资案例", None, "search"), ("列出交通事故案例", None, "search"),
    ("帮我生成文书", None, "document"), ("起草答辩状", "civil_defense", "document"),
])
async def test_every_graph_branch_terminates_with_standard_result(app, message, document_type, intent):
    # An empty candidate set is a valid branch outcome, not an infrastructure failure.
    class EmptyRetriever:
        def search(self, *args, **kwargs):
            return []
    events = []
    async def emit(name, data):
        events.append((name, data))
    graph = build_workflow(app.state.database, EmptyRetriever(), AgentLLM(), emit)
    state = await graph.ainvoke({"request_id": uuid4(), "user_id": uuid4(), "session_id": uuid4(), "payload": ChatRequest(message=message, document_type=document_type), "conversation_messages": [], "warnings": []}, {"recursion_limit": 10})
    result = state["result"]
    assert result.intent == intent
    assert result.response
    assert events[0][0] == "meta"
    assert "".join(data["delta"] for name, data in events if name == "content") == result.response
    if intent == "document":
        assert result.missing_fields
