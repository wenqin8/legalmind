"""Replay frozen RAG failures offline; never call a provider or alter baseline files."""

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agents.evidence import Evidence, validate_citations
from app.agents.qa import generate_qa
from app.agents.tasks import advance_task
from app.agents.workflow import build_workflow
from app.core.config import BACKEND_DIR
from app.core.errors import ModelUnavailableError
from app.db.base import Base
from app.db.session import Database
from app.evaluation.dataset import catalog_entries, sha256
from app.llm.base import LLMClient
from app.rag.bm25 import BM25Document, BM25Index
from app.rag.legal_catalog import import_catalog, retrieve_provisions
from app.schemas.chat import ChatRequest, SourceReference
from app.schemas.tasks import TaskState


class ReplayLLM(LLMClient):
    def __init__(self, outputs=None, stream_text=""):
        self.outputs = outputs or {}
        self.stream_text = stream_text
        self.calls = []
        self.closed = False

    async def complete(self, messages):
        task = messages[0].content.splitlines()[0]
        self.calls.append(task)
        if task not in self.outputs:
            raise AssertionError(f"Unexpected replay call: {task}")
        return self.outputs[task]

    async def stream(self, messages):
        try:
            for offset in range(0, len(self.stream_text), 7):
                yield self.stream_text[offset:offset + 7]
        finally:
            self.closed = True


class NoRetrieval:
    def search(self, *args, **kwargs):
        raise AssertionError("Date correction should not retrieve")


def call(turn, name):
    return next(c for c in turn["model_trace"] if c["task"] == name)


def selected_evidence(turn):
    sources = {c["source"]["citation_id"]: c["source"]
               for c in call(turn, "TASK:APPLICABILITY")["input"]["candidates"]}
    return [Evidence(SourceReference.model_validate(sources[e["citation_id"]]), e["text"])
            for e in call(turn, "TASK:QA")["input"]["evidence"]]


async def diagnose(raw):
    scenarios = {s["id"]: s for s in raw["scenarios"]}
    findings = {}
    routes = []
    for domain in ("MF", "LD", "TA", "CD"):
        scenario = scenarios[f"E-L-{domain}-06"]
        previous = TaskState.model_validate(scenario["turns"][0]["response"]["task"])
        turn = scenario["turns"][1]
        payload = ChatRequest(message=turn["expected"]["message"])
        llm = ReplayLLM({"TASK:INTENT": call(turn, "TASK:INTENT")["output"]})
        graph = build_workflow(None, NoRetrieval(), llm)
        state = await graph.ainvoke({"request_id": uuid4(), "user_id": uuid4(), "session_id": uuid4(),
            "payload": payload, "conversation_messages": [], "warnings": [], "task": previous})
        actual = state["result"].task
        assert actual.kind == "document" and actual.fields == {} and actual.task_id != previous.task_id
        # Counterfactual isolates the existing state reducer from the faulty router.
        extractor = ReplayLLM({"TASK:EXTRACT": json.dumps({"domain": previous.domain,
            "general_question": False, "fields": [{"name": "event_date", "value": "2026年7月1日",
                "quote": payload.message}]}, ensure_ascii=False)})
        corrected, _ = await advance_task(payload, previous, kind="qa", turn_id=uuid4(), llm=extractor)
        assert corrected.phase == "conflict" and corrected.task_id == previous.task_id
        assert corrected.fields["event_date"] == previous.fields["event_date"]
        accepted, _ = await advance_task(ChatRequest(message="确认修改"), corrected,
                                         kind="qa", turn_id=uuid4(), llm=extractor)
        assert accepted.fields["event_date"].value == "2026年7月1日"
        routes.append({"scenario": scenario["id"], "actual_kind": actual.kind,
                       "actual_fields": list(actual.fields), "actual_task_replaced": True,
                       "direct_qa_reducer_preserves_old_value": True,
                       "direct_qa_reducer_confirms_new_value": True,
                       "counterfactual_scope": "reducer with grounded extraction; not a repaired workflow"})
    findings["date_correction_replay"] = routes

    turn = scenarios["E-L-LD-01"]["turns"][0]
    evidence = selected_evidence(turn)
    draft = call(turn, "TASK:QA")["output"]
    matched = []
    for match in re.finditer(r'[“"]([^”"]+)[”"]\s*(\[S[1-5]\])?', draft):
        prefix = draft[max(0, match.start()-14):match.start()]
        if match[2] is None and re.search(r"(?:原文|条文|规定|法条|法律).{0,6}$", prefix):
            matched.append({"prefix": prefix, "phrase": match[1]})
    assert matched
    replay = ReplayLLM(stream_text=draft)
    yielded = []
    try:
        async for part in generate_qa(call(turn, "TASK:QA")["input"]["query"], [], evidence, replay):
            yielded.append(part)
    except ModelUnavailableError:
        pass
    else:
        raise AssertionError("Saved first paragraph should be rejected")
    # Same partial paragraph passes citation validation after removing term quotes.
    validate_citations(draft.replace("“", "").replace("”", ""), evidence)
    assert replay.closed and not yielded
    findings["quote_false_positive"] = {"scenario": "E-L-LD-01", "matched_phrases": matched,
        "replayed_error": "MODEL_UNAVAILABLE", "provider_calls": 0, "stream_closed": replay.closed,
        "emitted_paragraphs": len(yielded), "same_paragraph_without_quotes_passes_citation_check": True,
        "scope": "saved prefix only; full provider output was cancelled and is unavailable"}

    turn = scenarios["E-L-TA-16"]["turns"][0]
    validate_citations(call(turn, "TASK:QA")["output"], selected_evidence(turn))
    findings["unsupported_claim_is_not_structurally_rejected"] = {
        "scenario": "E-L-TA-16", "production_citation_check_passes": True,
        "evidence_articles": [e.source.reference_number for e in selected_evidence(turn)],
        "semantic_verdict": "manual source comparison required; this probe does not judge entailment"}

    entries = catalog_entries()
    database = Database("sqlite:///:memory:")
    try:
        Base.metadata.create_all(database.engine)
        import_catalog(database, entries)
        gate_results = []
        for scenario_id, target in (("E-L-LD-01", "labor_ii-2025-07-31-19"),
                                    ("E-L-TA-03", "personal_injury-2022-04-24-8"),
                                    ("E-L-TA-16", "personal_injury-2022-04-24-18")):
            scenario = scenarios[scenario_id]
            query = scenario["turns"][0]["expected"]["message"]
            eligible = [e for e in entries if scenario["domain"] in e.verification.domains
                        and e.record.legal_status.value == "effective"
                        and e.verification.effective_from <= datetime.now().date()
                        and (e.verification.effective_until is None or e.verification.effective_until > datetime.now().date())]
            target_entry = next(e for e in eligible if e.record.record_id == target)
            ranking = BM25Index([BM25Document(e.record.record_id, " ".join(e.verification.keywords)
                                  + " " + e.verification.original_text) for e in eligible]).search(query, limit=len(eligible))
            ranks = {key: i for i, (key, _) in enumerate(ranking, 1)}
            actual = retrieve_provisions(database, query, scenario["domain"], event_date=None, general=True)
            keyword_hits = [k for k in target_entry.verification.keywords if k in query]
            assert target in ranks and not keyword_hits and target not in [r.record_id for r, _ in actual]
            gate_results.append({"scenario": scenario_id, "target": target,
                "target_keywords": target_entry.verification.keywords, "matching_keywords": keyword_hits,
                "rank_before_keyword_gate": ranks[target], "would_be_in_ungated_top5": ranks[target] <= 5,
                "returned_ids": [r.record_id for r, _ in actual]})
        findings["keyword_gate_ablation"] = gate_results
        domains = []
        for scenario_id in ("E-L-TA-04", "E-L-CD-16"):
            scenario = scenarios[scenario_id]
            turn = scenario["turns"][0]
            assert json.loads(call(turn, "TASK:EXTRACT")["output"])["domain"] is None
            rows = retrieve_provisions(database, turn["expected"]["message"], scenario["domain"],
                                       event_date=None, general=True)
            hits = set(scenario["gold_sources"]) & {r.record_id for r, _ in rows}
            assert hits
            domains.append({"scenario": scenario_id, "recorded_domain": None,
                "recorded_legal_retrieval_executed": any(c["task"] == "TASK:APPLICABILITY" for c in turn["model_trace"]),
                "gold_domain_counterfactual_hits": sorted(hits), "scope": "oracle-domain diagnostic; not end-to-end improvement"})
        findings["domain_gate_counterfactual"] = domains
    finally:
        database.dispose()
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BACKEND_DIR.parent / "docs/acceptance/rag-v1-answers.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Choose a new output path; existing evidence is never overwritten")
    digest = sha256(args.input)
    findings = asyncio.run(diagnose(json.loads(args.input.read_text(encoding="utf-8"))))
    assert digest == sha256(args.input)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "input_sha256": digest,
              "diagnostic_script_sha256": sha256(Path(__file__)), "provider_calls": 0,
              "database": "new in-memory SQLite; default database untouched", "findings": findings}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
