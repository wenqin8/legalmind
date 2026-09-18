"""A bounded graph with a single output path for sync and streamed chat."""

from collections.abc import Awaitable, Callable
from typing import TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agents.evidence import Evidence, INSUFFICIENT, retrieve_evidence, retrieval_query, select_evidence, source_summary
from app.agents.intent import classify_intent
from app.agents.qa import generate_qa
from app.agents.tasks import advance_task, action_for, task_reply, QA_FIELDS, COMMANDS
from app.agents.intent import IntentDecision, DOCUMENT_NAMES, SEARCH_REQUEST
from app.agents.legal_evidence import legal_evidence
from app.rag.legal_catalog import event_interval
from app.schemas.tasks import TaskState
from app.core.errors import AppError
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever
from app.schemas.cases import DEMO_CASE_WARNING
from app.schemas.chat import CHAT_DISCLAIMER, ChatData, ChatRequest, ConversationMessage, IntentType, SourceReference
from app.schemas.documents import DocumentRequest
from app.services.documents import PreparedDocument, prepare_document

Emitter = Callable[[str, dict], Awaitable[None]]


async def discard_event(event: str, data: dict) -> None:
    pass


class AgentState(TypedDict, total=False):
    request_id: UUID
    user_id: UUID
    session_id: UUID
    payload: ChatRequest
    conversation_messages: list[ConversationMessage]
    intent: IntentType
    evidence: list[Evidence]
    response: str
    sources: list[SourceReference]
    missing_fields: list[str]
    warnings: list[str]
    document: PreparedDocument | None
    result: ChatData
    task: TaskState | None
    turn_id: UUID


def build_workflow(database: Database, retriever: HybridCaseRetriever, llm: LLMClient, emit: Emitter = discard_event):
    async def intent(state: AgentState):
        previous = state.get("task")
        request = state["payload"]
        action = action_for(request)
        if previous and previous.kind == "document" and previous.phase != "cancelled" and action != "restart" and not request.document_type and not SEARCH_REQUEST.search(request.message):
            names = [value for name, value in DOCUMENT_NAMES.items() if request.message.strip(" 。") == name]
            decision = IntentDecision(intent="document", document_type=names[0] if names else previous.document_type)
        else:
            decision = await classify_intent(request, llm)
        payload = state["payload"].model_copy(update={"document_type": decision.document_type})
        await emit("meta", {"request_id": str(state["request_id"]), "session_id": str(state["session_id"]), "intent": decision.intent})
        return {"intent": decision.intent, "payload": payload, "missing_fields": [], "document": None, "sources": []}

    async def qa(state: AgentState):
        query = state["payload"].message
        history = state["conversation_messages"]
        task, _ = await advance_task(state["payload"], state.get("task"), kind="qa", turn_id=state.get("turn_id", uuid4()), llm=llm)
        if task.domain or action_for(state["payload"]) == "cancel":
            # Old task facts cannot be carried into a different topic through prose history.
            history = [message for i in range(0, len(history) - 1, 2)
                       if history[i + 1].task and history[i + 1].task.task_id == task.task_id
                       for message in history[i:i + 2]]
            reserved = sum(len(k) + len(v.value) + 2 for k, v in task.fields.items())
            while history and reserved + sum(len(message.content) for message in history) > 12000:
                history = history[2:]
            if task.phase in {"collecting", "conflict", "cancelled"}:
                response = task_reply(task)
                await emit("content", {"delta": response})
                return {"task": task, "response": response, "missing_fields": task.missing_fields}
            if task.mode == "event" and event_interval(task.fields.get("event_date").value if task.fields.get("event_date") else "") is None:
                task.phase, task.missing_fields = "collecting", ["event_date"]
                task.questions = ["请补充关键事件的明确年份、月份或完整日期；相对时间或不确定日期不能用于选择法律版本。"]
                response = task_reply(task)
                await emit("content", {"delta": response})
                return {"task": task, "response": response, "missing_fields": task.missing_fields}
            legal, missing = await legal_evidence(database, query, task, llm)
            if missing:
                task.phase, task.missing_fields = "collecting", list(missing)
                task.questions = list(missing.values())
                response = task_reply(task)
                await emit("content", {"delta": response})
                return {"task": task, "response": response, "missing_fields": list(missing)}
            if legal:
                parts = []
                grounded_query = query + "\n用户此前提供并保留的事实（数据）：\n" + "\n".join(f"{k}: {v.value}" for k, v in task.fields.items())
                async for part in generate_qa(grounded_query, history, legal, llm):
                    parts.append(part)
                    await emit("content", {"delta": part})
                response = "".join(parts)
                return {"task": task, "response": response, "sources": [e.source for e in legal if f"[{e.source.citation_id}]" in response],
                        "warnings": state["warnings"] + ["法条使用本地核验版本，未在本次回答时实时联网更新；引用真实仍需核对场景、例外和过渡规则。"]}
        else:
            task = None
        candidates = await retrieve_evidence(retrieval_query(query, history), database, retriever)
        evidence = await select_evidence(query, history, candidates, llm)
        if not evidence:
            await emit("content", {"delta": INSUFFICIENT})
            return {"task": task, "response": INSUFFICIENT, "sources": [], "evidence": [], "warnings": state["warnings"] + ["没有可确认相关的资料，当前回答不提供具体法律结论。"]}
        parts = []
        async for part in generate_qa(query, history, evidence, llm):
            parts.append(part)
            await emit("content", {"delta": part})
        response = "".join(parts)
        sources = [e.source for e in evidence if f"[{e.source.citation_id}]" in response]
        return {"task": task, "response": response, "sources": sources, "evidence": evidence,
                "warnings": state["warnings"] + (["未找到可确认适用的法条版本；以下仅为演示参考，不能替代法律依据。"] if task else [])}

    async def search(state: AgentState):
        evidence = await retrieve_evidence(retrieval_query(state["payload"].message, state["conversation_messages"]), database, retriever)
        sources = [e.source for e in evidence]
        response = source_summary(sources)
        await emit("content", {"delta": response})
        return {"response": response, "sources": sources, "evidence": evidence}

    async def document(state: AgentState):
        payload = state["payload"]
        task, confirmed = await advance_task(payload, state.get("task"), kind="document", turn_id=state.get("turn_id", uuid4()), llm=llm)
        if not confirmed:
            response = task_reply(task)
            await emit("content", {"delta": response})
            return {"task": task, "response": response, "missing_fields": task.missing_fields}
        try:
            request = DocumentRequest(document_type=task.document_type, parameters={k: v.value for k, v in task.fields.items() if k != "additional_instructions"},
                                      additional_instructions=task.fields["additional_instructions"].value if "additional_instructions" in task.fields else "", use_references=True)
            prepared = await prepare_document(request, database, retriever, llm)
        except ValidationError as exc:
            raise AppError(status_code=422, code="VALIDATION_ERROR", message="文书参数不正确") from exc
        except AppError as exc:
            if exc.code != "DOCUMENT_FIELDS_MISSING":
                raise
            fields = (exc.details or {})["fields"]
            response = "请通过结构化参数补充以下信息：" + "、".join(field["message"].removeprefix("请填写") for field in fields) + "。"
            await emit("content", {"delta": response})
            return {"response": response, "missing_fields": [field["name"] for field in fields]}
        await emit("content", {"delta": prepared.data.content})
        task.document_id = prepared.data.document_id
        return {"task": task, "response": prepared.data.content, "sources": prepared.data.sources, "document": prepared, "warnings": state["warnings"] + prepared.data.warnings}

    async def finalize(state: AgentState):
        warnings = list(dict.fromkeys([CHAT_DISCLAIMER, *state["warnings"]]))
        if any(source.is_demo for source in state["sources"]):
            warnings.append(DEMO_CASE_WARNING)
        prepared = state.get("document")
        result = ChatData(response=state["response"], intent=state["intent"], sources=state["sources"],
                          session_id=state["session_id"], missing_fields=state["missing_fields"],
                          warnings=list(dict.fromkeys(warnings)), document_id=prepared.data.document_id if prepared else (state.get("task").document_id if state.get("task") else None), task=state.get("task"))
        return {"result": result}

    graph = StateGraph(AgentState)
    graph.add_node("intent", intent)
    graph.add_node("qa", qa)
    graph.add_node("search", search)
    graph.add_node("document", document)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", lambda state: state["intent"], {name: name for name in ("qa", "search", "document")})
    for name in ("qa", "search", "document"):
        graph.add_edge(name, "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
