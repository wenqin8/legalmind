"""Deterministic graph dependencies, separate from production fallback behavior."""

import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import Case
from app.llm.fake import FakeLLMClient
from app.rag.importer import import_cases, load_case_records
from app.rag.retriever import SearchHit


class AgentLLM(FakeLLMClient):
    def __init__(self):
        super().__init__("结论\n可根据演示情景整理证据[S1]。\n\n风险\n当前资料不足以支持具体法律结论。\n\n下一步\n核对工作记录。", chunk_size=5)
        self.requests = []
        self.stream_calls = 0
        self.selection = True

    async def complete(self, messages):
        self.requests.append(tuple(messages))
        self.call_count += 1
        if "TASK:INTENT" in messages[0].content:
            return '{"intent":"qa","confidence":0.9}'
        if 'TASK:EXTRACT' in messages[0].content:
            return '{"domain":null,"general_question":false,"requires_local_material":false,"fields":[]}'
        if "TASK:EVIDENCE" in messages[0].content:
            candidates = json.loads(messages[1].content)["candidates"]
            return json.dumps({"in_scope": self.selection, "source_ids": [candidates[0]["source_id"]] if self.selection and candidates else []})
        if 'TASK:CONDITIONS' in messages[0].content:
            data = json.loads(messages[1].content)
            return json.dumps({'items': [{'unit_id': u['unit_id'], 'verdict': 'consistent'} for u in data['units']]})
        if 'TASK:GROUNDING' in messages[0].content:
            # Explicitly scripted verifier for transport/state tests; semantic rejection
            # is tested independently with adversarial checker responses.
            data = json.loads(messages[1].content)
            import re
            items = []
            for unit in data['units']:
                labels = re.findall(r'\[(S[1-5])\]', unit['text'])
                spans = [{'citation_id': e['citation_id'], 'span_id': e['spans'][0]['span_id']} for e in data['evidence'] if e['citation_id'] in labels]
                items.append({'unit_id': unit['unit_id'], 'verdict': 'supported' if spans else 'neutral', 'supports': spans})
            return json.dumps({'items': items})
        return self.response

    async def stream(self, messages):
        self.requests.append(tuple(messages))
        self.stream_calls += 1
        async for part in super().stream(messages):
            yield part


class StaticRetriever:
    def __init__(self, case):
        self.case = case
        self.queries = []

    def search(self, query, **kwargs):
        self.queries.append(query)
        return [SearchHit(self.case, 0.03, 1, 1)]


def configure_agent(app):
    records = load_case_records(Path(__file__).resolve().parents[1] / "data/demo/cases.jsonl")
    import_cases(app.state.database, records)
    with app.state.database.session() as session, session.begin():
        case = session.scalar(select(Case).where(Case.case_number == "DEMO-LABOR_DISPUTE-001"))
        case.import_status = "indexed"
    app.state.case_retriever = StaticRetriever(case)
    app.state.llm_client = AgentLLM()
