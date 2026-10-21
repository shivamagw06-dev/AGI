"""Calibrated overall confidence from evidence, reasoning, portfolio, forecast, learning, consensus."""

from __future__ import annotations

from typing import Any


def compute_confidence(
    *,
    evidence: dict[str, Any],
    weights: dict[str, Any],
    conflicts: dict[str, Any],
    uncertainty: dict[str, Any],
    inputs: dict[str, Any],
    committee: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layers = inputs.get("layers") or {}
    summary = inputs.get("stack_summary") or {}

    evidence_score = float(evidence.get("coverage") or 0)
    reasoning_score = 0.85 if weights.get("transparent") and abs(float(weights.get("sum") or 0) - 1.0) < 0.02 else 0.5
    portfolio_score = 0.7
    if summary.get("portfolio_quality") is not None:
        try:
            portfolio_score = min(1.0, float(summary["portfolio_quality"]) / 100.0)
        except Exception:
            portfolio_score = 0.65
    elif (layers.get("portfolio_intelligence") or {}).get("portfolio_quality") is not None:
        try:
            portfolio_score = min(1.0, float(layers["portfolio_intelligence"]["portfolio_quality"]) / 100.0)
        except Exception:
            portfolio_score = 0.65

    forecast_score = float(
        summary.get("forecast_confidence")
        or (layers.get("forecast_intelligence") or {}).get("confidence")
        or 0.55
    )
    if forecast_score > 1:
        forecast_score = forecast_score / 100.0

    learning_score = 0.55
    if summary.get("memory_thinking_improved") is True or (layers.get("institutional_memory") or {}).get(
        "thinking_improved"
    ):
        learning_score = 0.75
    elif summary.get("memory_lesson_count") or (layers.get("institutional_memory") or {}).get("lesson_count"):
        learning_score = 0.65

    committee = committee or {}
    consensus_score = 0.6
    if committee.get("committee_stance"):
        consensus_score = 0.72
    if conflicts.get("conflict_count", 0) >= 2:
        consensus_score -= 0.12
    if uncertainty.get("dominant") in {"conflicting_evidence", "unknown_unknown"}:
        consensus_score -= 0.08

    components = {
        "evidence": round(evidence_score, 3),
        "reasoning": round(reasoning_score, 3),
        "portfolio": round(max(0.2, min(1.0, portfolio_score)), 3),
        "forecast": round(max(0.2, min(1.0, forecast_score)), 3),
        "historical_accuracy": round(learning_score, 3),
        "learning": round(learning_score, 3),
        "committee_consensus": round(max(0.2, min(1.0, consensus_score)), 3),
    }
    overall = round(sum(components.values()) / len(components), 3)
    return {
        "confidence": overall,
        "components": components,
        "calibrated_continuously": True,
        "rule": "Overall confidence = evidence · reasoning · portfolio · forecast · historical accuracy · learning · committee consensus",
    }
