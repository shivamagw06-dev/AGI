"""Forecast confidence — evidence coverage, analogue strength, uncertainty penalty."""

from __future__ import annotations

from typing import Any


def forecast_confidence(
    *,
    probabilities: dict[str, Any],
    uncertainty: dict[str, Any],
    evidence: dict[str, Any],
    triggers: dict[str, Any],
) -> dict[str, Any]:
    coverage = float(probabilities.get("evidence_coverage") or 0.5)
    u = float(uncertainty.get("uncertainty_score") or 0.4)
    evid_count = float((evidence or {}).get("count") or 0)
    evid_factor = min(1.0, evid_count / 8.0)
    trigger_ok = 1.0 if triggers.get("all_triggers_observable") else 0.5
    raw = 0.35 * coverage + 0.25 * evid_factor + 0.2 * trigger_ok + 0.2 * (1.0 - u)
    overall = round(max(0.15, min(0.9, raw)), 3)
    if overall >= 0.7:
        label = "high"
    elif overall >= 0.5:
        label = "moderate"
    else:
        label = "low"
    return {
        "confidence": overall,
        "label": label,
        "components": {
            "evidence_coverage": coverage,
            "evidence_count_factor": round(evid_factor, 3),
            "trigger_observability": trigger_ok,
            "uncertainty_penalty": u,
        },
        "rule": "Confidence reflects scenario evidence — never certainty of a price path",
        "not_a_price_prediction": True,
    }
