"""Cash Quality Engine — are earnings cash-backed?"""

from __future__ import annotations

from typing import Any


def cash_quality(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    conv = float(b.get("cash_conversion") or 0.7)
    trend = str(b.get("trend") or "stable").lower()
    cfo_vs_ni = str(b.get("cfo_vs_ni") or "").lower()

    score = conv * 85.0
    if "strong" in cfo_vs_ni or "accretive" in cfo_vs_ni:
        score += 10
    elif "weak" in cfo_vs_ni or "deterior" in cfo_vs_ni:
        score -= 20
    if trend == "improving":
        score += 5
    elif trend in {"deteriorating", "cash_deterioration"}:
        score -= 12
    score = max(0.0, min(100.0, score))

    return {
        "cash_quality": round(score, 1),
        "cash_conversion": conv,
        "cfo_vs_ni": b.get("cfo_vs_ni"),
        "fcf_proxy": b.get("fcf_proxy"),
        "trend": trend,
        "cash_signal": "cash_improvement"
        if trend == "improving"
        else "cash_deterioration"
        if "deterior" in trend
        else "stable",
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
    }
