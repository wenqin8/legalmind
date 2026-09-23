"""Explicit denominators, graded ranking metrics and failure-preserving aggregates."""

import math
from statistics import mean


def ranking_metrics(ranking: list[str], relevance: dict[str, int], k: int) -> dict:
    if k < 1 or len(ranking) != len(set(ranking)):
        raise ValueError("Positive k and unique ranked identifiers are required")
    if any(grade not in (1, 2, 3) for grade in relevance.values()):
        raise ValueError("Relevance grades must be 1, 2 or 3")
    top = ranking[:k]
    matches = sum(key in relevance for key in top)
    dcg = sum((2 ** relevance.get(key, 0) - 1) / math.log2(i + 2) for i, key in enumerate(top))
    ideal = sum((2 ** grade - 1) / math.log2(i + 2) for i, grade in enumerate(sorted(relevance.values(), reverse=True)[:k]))
    return {
        "hit": float(matches > 0) if relevance else None,
        "recall": matches / len(relevance) if relevance else None,
        # Missing slots count as non-relevant. Do not inflate precision by returning one item.
        "precision": matches / k,
        "ndcg": dcg / ideal if ideal else None,
        "reciprocal_rank": next((1 / i for i, key in enumerate(top, 1) if key in relevance), 0.0) if relevance else None,
        "recall_ceiling": min(k, len(relevance)) / len(relevance) if relevance else None,
        "negative_false_retrieval": bool(top) if not relevance else None,
    }


def percentile(values: list[float], proportion: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * proportion
    lower = math.floor(index)
    return values[lower] + (values[math.ceil(index)] - values[lower]) * (index - lower)


def aggregate(rows: list[dict]) -> dict:
    successful = [row for row in rows if row.get("error") is None]
    result = {"queries": len(rows), "successful_queries": len(successful),
              "service_errors": len(rows) - len(successful),
              "latency_ms_p50": percentile([r['latency_ms'] for r in successful], .5),
              "latency_ms_p95": percentile([r['latency_ms'] for r in successful], .95)}
    for k in (1, 3, 5):
        for metric in ("hit", "recall", "precision", "ndcg", "reciprocal_rank", "recall_ceiling", "negative_false_retrieval"):
            values = [row["metrics"][str(k)][metric] for row in successful if row["metrics"][str(k)][metric] is not None]
            result[f"{metric}@{k}"] = {"value": mean(values) if values else None, "denominator": len(values)}
    positive = [row for row in rows if row["answerable"]]
    result["effective_hit@5_including_errors"] = {
        "value": sum(bool(row.get('metrics', {}).get('5', {}).get('hit')) for row in positive) / len(positive) if positive else None,
        "denominator": len(positive),
    }
    temporal = [item for row in successful for item in row.get("version_checks", [])]
    result["returned_version_match_rate"] = {"value": mean(temporal) if temporal else None, "denominator": len(temporal)}
    return result
