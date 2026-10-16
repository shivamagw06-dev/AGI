"""Per-decision quality metrics. Measurement only — never reasons."""

from __future__ import annotations

from typing import Any


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def compute_decision_metrics(decision: dict[str, Any]) -> dict[str, Any]:
    evidence = decision.get("evidence_pack") or {}
    research = decision.get("research") or {}
    portfolio = decision.get("portfolio") or {}
    og = decision.get("outcome_graph") or {}
    confidence = float(decision.get("confidence") or 0.0)

    completeness = float(evidence.get("completeness") or 0.0)
    freshness_days = float(evidence.get("freshness_days") or 999)
    evidence_quality = float(evidence.get("quality_score") or completeness * 100.0)
    freshness = _clamp(100.0 - freshness_days * 2.0)

    research_quality = float(research.get("quality_score") or 0.0)
    portfolio_quality = float(portfolio.get("sizing_quality") or 0.0)

    outcome_available = bool(og.get("available"))
    prediction_correct = decision.get("prediction_correct")
    fw_ok = decision.get("framework_selection_correct")

    if not outcome_available:
        return {
            "decision_id": decision.get("decision_id"),
            "outcome_available": False,
            "insufficient": True,
            "reason": "outcome_unavailable",
            "fabricated": False,
            "metrics": {
                "evidence_completeness": round(completeness * 100.0, 2),
                "evidence_freshness": round(freshness, 2),
                "evidence_quality": round(evidence_quality, 2),
                "research_quality": round(research_quality, 2),
                "portfolio_quality": round(portfolio_quality, 2),
                "framework_selection_accuracy": 100.0 if fw_ok else (0.0 if fw_ok is False else None),
            },
            "note": "Outcome missing — refusing to fabricate accuracy metrics.",
        }

    decision_accuracy = 100.0 if prediction_correct else 0.0
    outcome_accuracy = decision_accuracy
    framework_selection_accuracy = 100.0 if fw_ok else 0.0

    # Calibration: how close confidence was to realised binary outcome
    realised = 1.0 if prediction_correct else 0.0
    calibration_error = abs(confidence - realised)
    confidence_calibration = _clamp(100.0 * (1.0 - calibration_error))

    # Scenario / risk / timing / execution proxies from outcome graph
    alpha = float(og.get("alpha") or 0.0)
    drawdown = float(og.get("drawdown") or 0.0)
    risk_quality = _clamp(80.0 + drawdown * 100.0)  # less negative DD → higher
    scenario_accuracy = 90.0 if prediction_correct else 35.0
    timing_quality = _clamp(70.0 + alpha * 100.0)
    execution_quality = portfolio_quality
    learning = decision.get("learning_proposal") or {}
    learning_effectiveness = (
        85.0
        if learning.get("status") in {"approved", "deployed"}
        else 60.0
        if learning
        else 40.0
    )

    # Framework success for this decision equals outcome when framework correct, else dampened
    if fw_ok and prediction_correct:
        framework_success_rate = 100.0
    elif fw_ok and not prediction_correct:
        framework_success_rate = 40.0
    else:
        framework_success_rate = 15.0

    metrics = {
        "decision_accuracy": decision_accuracy,
        "evidence_completeness": round(completeness * 100.0, 2),
        "evidence_freshness": round(freshness, 2),
        "evidence_quality": round(evidence_quality, 2),
        "framework_selection_accuracy": framework_selection_accuracy,
        "framework_success_rate": framework_success_rate,
        "research_quality": round(research_quality, 2),
        "portfolio_quality": round(portfolio_quality, 2),
        "risk_quality": round(risk_quality, 2),
        "scenario_accuracy": scenario_accuracy,
        "confidence_calibration": round(confidence_calibration, 2),
        "timing_quality": round(timing_quality, 2),
        "execution_quality": round(execution_quality, 2),
        "outcome_accuracy": outcome_accuracy,
        "learning_effectiveness": learning_effectiveness,
        "calibration_error": round(calibration_error, 4),
        "expected_confidence": confidence,
        "realised_accuracy": realised,
    }
    return {
        "decision_id": decision.get("decision_id"),
        "outcome_available": True,
        "insufficient": False,
        "fabricated": False,
        "metrics": metrics,
    }
