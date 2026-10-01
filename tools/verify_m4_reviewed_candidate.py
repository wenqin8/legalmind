"""Offline input/source/retrieval checks; never generate or score model answers."""
import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
from app.db.base import Base
from app.db.session import Database
from app.evaluation.dataset import sha256
from app.evaluation.metrics import ranking_metrics
from app.evaluation.offline_guard import OfflineGuard
from app.evaluation.once_acceptance import implementation_digest, load_package
from app.rag.catalog_profiles import PROFILE_PATHS, catalog_identity, profile_entries
from app.rag.legal_catalog import import_catalog, retrieve_provisions


def evaluate(package):
    manifest, queries, scenarios = load_package(package)
    rubric = json.loads((package / "rubric.json").read_text(encoding="utf-8"))
    rubric_by_id = {item["query_id"]: item for item in rubric["items"]}
    assert len(rubric_by_id) == len(queries) == len(scenarios) == 24
    baseline_runtime = implementation_digest()
    baseline_files = {name: sha256(package / name) for name in ["manifest.json", *manifest["files"]]}
    receipt_path = package / "observation-receipt.json"
    receipt_before = sha256(receipt_path) if receipt_path.exists() else None
    guard = OfflineGuard()
    database = Database("sqlite://")
    results = []
    try:
        with guard:
            entries = profile_entries(manifest["corpus_profile"])
            catalog_by_id = {entry.record.record_id: entry for entry in entries}
            Base.metadata.create_all(database.engine)
            import_catalog(database, entries)
            identity = catalog_identity(database)
            assert identity["profile"] == "eval-rag-v2-209" and identity["provision_count"] == 209
            for query in queries:
                item = rubric_by_id[query.id]
                source_checks = {"behavior_consistent": item["expected"] == query.expected_behavior,
                    "gold_sources_exist": set(query.relevance).issubset(catalog_by_id),
                    "criterion_present": bool(item["criterion"]), "nonexpert_status_retained": item["review_status"] == "agent_draft_pending_expert"}
                if query.expected_behavior == "answer":
                    source = catalog_by_id[item["source_record_id"]]
                    source_checks.update({"source_matches_gold": item["source_record_id"] in query.relevance,
                        "title_matches": item["title"] == source.record.regulation_name,
                        "article_matches": item["article"] == source.record.article_number,
                        "text_matches": item["original_text"] == source.verification.original_text,
                        "metadata_matches": item["source_verification"] == source.verification.model_dump(mode="json")})
                started = time.perf_counter()
                rows = retrieve_provisions(database, query.query, query.domain, event_date=query.event_date, general=query.general)
                ranking = [row.record_id for row, _ in rows]
                gold = {key: value.grade for key, value in query.relevance.items()}
                checks = {**source_checks, "candidate_count_at_most_five": len(ranking) <= 5,
                    "all_candidates_in_frozen_corpus": set(ranking).issubset(catalog_by_id)}
                results.append({"query_id": query.id, "domain": query.domain, "expected_behavior": query.expected_behavior,
                    "checks": checks, "ranking": ranking, "gold": gold,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    "direct_gold_hit_at_5": bool(set(ranking) & set(gold)) if gold else None,
                    "ranking_metrics": ranking_metrics(ranking, gold, 5) if gold else None,
                    "note": "Candidate retrieval is not an answerability or semantic judgment; empty gold is not automatically an error."})
    finally:
        database.dispose()
    positives = [row for row in results if row["expected_behavior"] == "answer"]
    hits = sum(row["direct_gold_hit_at_5"] for row in positives)
    checks_passed = all(all(row["checks"].values()) for row in results)
    assert baseline_files == {name: sha256(package / name) for name in baseline_files}
    assert baseline_runtime == implementation_digest()
    assert receipt_before == (sha256(receipt_path) if receipt_path.exists() else None)
    return {"recorded_at": datetime.now(timezone.utc).isoformat(), "scope": "offline_input_source_and_candidate_retrieval_preflight",
        "package": package.relative_to(ROOT).as_posix(), "package_manifest_sha256": sha256(package / "manifest.json"),
        "checker_sha256": sha256(Path(__file__)), "model_observation_receipt_preexisting": receipt_before is not None,
        "model_observation_receipt_sha256": receipt_before,
        "implementation_sha256": baseline_runtime, "catalog": identity,
        "corpus_files": {name: sha256(ROOT / "backend" / name) for name in PROFILE_PATHS[manifest["corpus_profile"]]},
        "complete": len(results) == 24, "input_source_checks_passed": checks_passed,
        "behavior_counts": dict(Counter(query.expected_behavior for query in queries)),
        "direct_hit_at_5": {"hits": hits, "denominator": len(positives), "value": hits / len(positives)},
        "retrieval_preflight_passed": hits == len(positives), "blocked_network_attempts": len(guard.attempts),
        "real_model_calls": 0, "actual_answers_generated": 0, "actual_answers_reviewed": 0,
        "model_answer_quality_passed": None, "independent_expert_review_complete": False,
        "legal_quality_acceptance_passed": False, "package_inputs_unchanged": True,
        "model_observation_receipt_created": False, "independent_blind_test": False, "results": results,
        "limitations": ["These questions and retrieval results have been examined during development; this is not blind testing.",
            "Gold domain/general-rule flags are supplied by the input; model extraction and applicability are not tested.",
            "Sixteen positive sources are checked; four clarification and four corpus-gap cases do not enter that denominator.",
            "Candidate hits, source equality and offline checks do not certify generated legal answers."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Refusing to overwrite earlier evidence")
    report = evaluate(args.package.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ["complete", "input_source_checks_passed", "direct_hit_at_5",
        "retrieval_preflight_passed", "blocked_network_attempts", "real_model_calls", "actual_answers_generated"]}))
    return 0 if report["input_source_checks_passed"] and report["retrieval_preflight_passed"] and not report["blocked_network_attempts"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
