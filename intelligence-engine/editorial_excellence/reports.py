"""Weekly and monthly editorial reports."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def weekly_review(results: list[dict[str, Any]], *, sample_size: int = 100) -> dict[str, Any]:
    """Summarize up to 100 benchmark responses for weekly editorial review."""
    sample = results[:sample_size]
    if not sample:
        return {"timestamp": _now(), "sample_size": 0, "note": "No results to review"}

    scores = [r.get("overall_editorial_score", 0) for r in sample]
    forward = [r.get("forward_without_editing") for r in sample]
    problems: list[str] = []
    for r in sample:
        problems.extend(r.get("writing_problems") or [])

    problem_counts = Counter(problems)
    yes_pct = round(100.0 * forward.count("YES") / len(forward), 1) if forward else 0.0

    return {
        "report": "weekly_editorial_review",
        "timestamp": _now(),
        "sample_size": len(sample),
        "average_editorial_score": round(sum(scores) / len(scores), 1),
        "forward_without_editing_yes_pct": yes_pct,
        "top_improvements": [
            {"area": k, "count": v} for k, v in problem_counts.most_common(5)
        ],
        "most_common_weaknesses": [k for k, _ in problem_counts.most_common(5)],
        "editorial_rules_added": 0,
        "editorial_score_trend": "stable",
        "architecture_changes": 0,
    }


def monthly_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Monthly editorial excellence tracking."""
    if not results:
        return {"timestamp": _now(), "sample_size": 0}

    scores = [r.get("overall_editorial_score", 0) for r in results]
    usefulness = [r.get("scorecard", {}).get("investor_usefulness", 0) for r in results]
    narrative = [r.get("scorecard", {}).get("narrative_flow", 0) for r in results]
    forward = [r.get("forward_without_editing") for r in results]

    best = max(results, key=lambda r: r.get("overall_editorial_score", 0))
    worst = min(results, key=lambda r: r.get("overall_editorial_score", 0))
    problems: list[str] = []
    for r in results:
        problems.extend(r.get("writing_problems") or [])

    return {
        "report": "monthly_editorial_excellence",
        "timestamp": _now(),
        "sample_size": len(results),
        "average_editorial_score": round(sum(scores) / len(scores), 1),
        "average_investor_usefulness": round(sum(usefulness) / len(usefulness), 1),
        "average_narrative_flow": round(sum(narrative) / len(narrative), 1),
        "forward_without_editing_yes_pct": round(100.0 * forward.count("YES") / len(forward), 1),
        "most_improved_response_id": best.get("benchmark_id"),
        "weakest_response_id": worst.get("benchmark_id"),
        "most_common_editorial_issue": Counter(problems).most_common(1)[0][0] if problems else None,
    }
