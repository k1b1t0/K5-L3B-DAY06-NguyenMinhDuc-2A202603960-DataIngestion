"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and gold evidence; return hit@1 and hit@3 trace for a query."""
    gold_page = question.get("gold_page")
    evidence = (question.get("evidence_quote") or "").strip()

    def is_hit(hit: dict[str, Any]) -> bool:
        page_match = hit.get("page") == gold_page
        evidence_match = bool(evidence and evidence in hit.get("text", ""))
        return page_match and evidence_match

    hit_at_1 = bool(hits and is_hit(hits[0]))
    hit_at_3 = any(is_hit(h) for h in hits[:3])

    return {
        "question_id": question.get("id"),
        "split": question.get("split", "dev"),
        "question": question.get("question"),
        "strategy": question.get("strategy"),
        "gold_page": gold_page,
        "evidence_quote": question.get("evidence_quote"),
        "hit@1": hit_at_1,
        "hit@3": hit_at_3,
        "hits": hits,
    }


def _calc_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate total, counts, rates and ratio strings for a group of traces."""
    total = len(items)
    if total == 0:
        return {
            "total": 0,
            "hit@1_count": 0,
            "hit@1_rate": 0.0,
            "hit@1_ratio": "0/0",
            "hit@3_count": 0,
            "hit@3_rate": 0.0,
            "hit@3_ratio": "0/0",
        }
    h1_count = sum(1 for t in items if t.get("hit@1"))
    h3_count = sum(1 for t in items if t.get("hit@3"))
    return {
        "total": total,
        "hit@1_count": h1_count,
        "hit@1_rate": round(h1_count / total, 4),
        "hit@1_ratio": f"{h1_count}/{total}",
        "hit@3_count": h3_count,
        "hit@3_rate": round(h3_count / total, 4),
        "hit@3_ratio": f"{h3_count}/{total}",
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    # Check if traces contain multiple strategies
    strategies = {t.get("strategy") for t in traces if t.get("strategy")}
    
    if strategies:
        result = {}
        for strat in sorted(strategies):
            strat_traces = [t for t in traces if t.get("strategy") == strat]
            dev_traces = [t for t in strat_traces if t.get("split") == "dev"]
            test_traces = [t for t in strat_traces if t.get("split") == "test"]
            result[strat] = {
                "dev": _calc_metrics(dev_traces),
                "test": _calc_metrics(test_traces),
                "overall": _calc_metrics(strat_traces),
            }
        return result

    # Single strategy or direct trace list
    dev_traces = [t for t in traces if t.get("split") == "dev"]
    test_traces = [t for t in traces if t.get("split") == "test"]
    return {
        "dev": _calc_metrics(dev_traces),
        "test": _calc_metrics(test_traces),
        "overall": _calc_metrics(traces),
    }
