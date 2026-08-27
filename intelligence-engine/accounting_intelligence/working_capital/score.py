"""Working Capital Engine."""

from __future__ import annotations

from typing import Any


def working_capital(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    efficiency = str(b.get("efficiency") or "stable").lower()
    dso = str(b.get("dso_trend") or "stable").lower()
    coverage_gap = bool(b.get("coverage_gap"))

    score = 70.0
    if efficiency in {"improving", "efficiency_improvement"}:
        score += 15
        signal = "efficiency_improvement"
    elif efficiency in {"watch", "deteriorating", "efficiency_deterioration"}:
        score -= 15
        signal = "efficiency_deterioration"
    else:
        signal = "stable"

    if "deterior" in dso or dso == "worsening":
        score -= 10
    elif dso == "improving":
        score += 8
    if coverage_gap:
        score -= 5
    score = max(0.0, min(100.0, score))

    return {
        "working_capital": round(score, 1),
        "efficiency_signal": signal,
        "dso_trend": dso,
        "dio_trend": b.get("dio_trend"),
        "dpo_trend": b.get("dpo_trend"),
        "casa": b.get("casa"),
        "nim": b.get("nim"),
        "coverage_gap": coverage_gap,
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
    }
