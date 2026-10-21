"""Aggregate CIE confidence."""

from __future__ import annotations

from typing import Any

from context_intelligence.schema import CONFIDENCE_THRESHOLD


def score_confidence(parts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scores = []
    detail = {}
    for key, row in parts.items():
        if not isinstance(row, dict):
            continue
        c = float(row.get("confidence") or 0.0)
        detail[key] = round(c, 4)
        scores.append(c)
    overall = round(sum(scores) / len(scores), 4) if scores else 0.0
    return {
        "overall": overall,
        "by_dimension": detail,
        "threshold": CONFIDENCE_THRESHOLD,
        "passes_threshold": overall >= CONFIDENCE_THRESHOLD,
    }
