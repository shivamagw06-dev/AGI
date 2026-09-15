"""Incentive alignment with shareholders."""

from __future__ import annotations

from typing import Any


def incentive_score(raw: dict[str, Any] | None) -> dict[str, Any]:
    r = dict(raw or {})
    score = float(r.get("score", 65))
    align = str(r.get("alignment") or "unknown")
    if align == "aligned":
        score = max(score, 75)
    elif align == "misaligned":
        score = min(score, 40)
    return {
        "incentives": round(score, 1),
        "alignment": align,
        "long_term_incentives": r.get("long_term_incentives"),
        "notes": r.get("notes"),
    }
