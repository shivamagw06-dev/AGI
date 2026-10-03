"""Earnings Quality Engine — is reported earnings real and persistent?"""

from __future__ import annotations

from typing import Any


def earnings_quality(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    recurring = float(b.get("recurring_share") or 0.7)
    one_offs = str(b.get("one_offs") or "medium").lower()
    persistence = str(b.get("persistence") or "medium").lower()
    prior = str(b.get("label_prior") or "")

    score = 50.0 + recurring * 40.0
    if one_offs in {"low", "nil", "none"}:
        score += 8
    elif one_offs in {"high", "elevated"}:
        score -= 15
    if persistence == "high":
        score += 8
    elif persistence == "low":
        score -= 12
    if str(b.get("exceptional_items") or "").lower() in {"nil_disclosed", "nil", "none", "low"}:
        score += 4
    score = max(0.0, min(100.0, score))

    if prior in {"High", "Medium", "Low", "Questionable"}:
        label = prior
    elif score >= 80:
        label = "High"
    elif score >= 60:
        label = "Medium"
    elif score >= 40:
        label = "Low"
    else:
        label = "Questionable"

    return {
        "earnings_quality": round(score, 1),
        "label": label,
        "recurring_share": recurring,
        "one_offs": one_offs,
        "persistence": persistence,
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
        "streams": {
            "recurring": label if recurring >= 0.9 else "Medium",
            "one_off_gains": "Low" if one_offs in {"low", "nil", "none"} else "Watch",
            "core_earnings": label,
        },
    }
