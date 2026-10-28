"""Credibility engine — statements tracked to outcomes over time."""

from __future__ import annotations

from typing import Any


def credibility_score(claims: list[dict[str, Any]]) -> dict[str, Any]:
    if not claims:
        return {"credibility": 55.0, "correct": 0, "incorrect": 0, "partial": 0, "claims": []}
    correct = sum(1 for c in claims if c.get("outcome") == "correct")
    partial = sum(1 for c in claims if c.get("outcome") == "partially_correct")
    incorrect = sum(1 for c in claims if c.get("outcome") == "incorrect")
    n = max(1, len(claims))
    score = round(100.0 * (correct + 0.5 * partial) / n, 1)
    return {
        "credibility": score,
        "correct": correct,
        "incorrect": incorrect,
        "partial": partial,
        "n": len(claims),
        "claims": claims,
        "rule": "Every management claim stores date → outcome → correct/incorrect/partial",
    }
