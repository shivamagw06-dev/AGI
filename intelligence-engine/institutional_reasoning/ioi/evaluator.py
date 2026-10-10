"""Module 3 — Prediction Evaluator.

Compare expected vs actual. Score every recommendation. No learning.
"""

from __future__ import annotations

from typing import Any

EVALUATOR_VERSION = "prediction-evaluator-v1.0.0"


def _f(v: Any, default: float | None = None) -> float | None:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def evaluate_prediction(
    lifecycle: dict[str, Any],
    market: dict[str, Any],
) -> dict[str, Any]:
    if not market.get("found"):
        return {
            "found": False,
            "evaluator_version": EVALUATOR_VERSION,
            "reason": "market_outcome_unavailable",
            "score": None,
        }

    expected = _f(lifecycle.get("expected_return"), 0.0) or 0.0
    expected_downside = _f(lifecycle.get("expected_downside"), 0.0) or 0.0
    actual = _f(market.get("total_return"), 0.0) or 0.0
    max_dd = _f(market.get("maximum_drawdown"), 0.0) or 0.0
    conf = _f((lifecycle.get("decision") or {}).get("confidence"), 0.7) or 0.7

    return_error = round(actual - expected, 6)
    abs_return_error = abs(return_error)
    downside_error = round(max(0.0, max_dd - expected_downside), 6)

    # Timing: if action was Increase and alpha negative early → timing error proxy
    action = str((lifecycle.get("decision") or {}).get("action") or "")
    alpha = _f(market.get("alpha"), 0.0) or 0.0
    timing_error = 0.0
    if action in {"Increase", "Hold"} and alpha < -0.05:
        timing_error = round(abs(alpha), 6)
    elif action in {"Reduce", "Exit"} and alpha > 0.05:
        timing_error = round(alpha * 0.5, 6)

    # Scenario accuracy
    realised = str(market.get("scenario_realised") or "")
    scenarios = lifecycle.get("scenarios") or {}
    scenario_accuracy = 0.7
    if realised:
        key = realised.lower()
        if key in scenarios:
            pred = _f((scenarios.get(key) or {}).get("expected_return"), 0.0) or 0.0
            scenario_accuracy = max(0.0, 1.0 - min(1.0, abs(actual - pred) / 0.25))
        elif key in {"bear", "stress"} and actual < 0:
            scenario_accuracy = 0.85
        elif key in {"bull", "base"} and actual >= 0:
            scenario_accuracy = 0.8
        else:
            scenario_accuracy = 0.35

    # Confidence accuracy: high confidence + large error → poor calibration
    confidence_accuracy = max(0.0, 1.0 - (abs_return_error * conf) / 0.25)
    confidence_accuracy = round(min(1.0, confidence_accuracy), 4)

    # Composite score 0-100
    score = round(
        100.0
        * (
            0.35 * max(0.0, 1.0 - abs_return_error / 0.25)
            + 0.20 * max(0.0, 1.0 - downside_error / 0.20)
            + 0.15 * max(0.0, 1.0 - timing_error / 0.15)
            + 0.15 * scenario_accuracy
            + 0.15 * confidence_accuracy
        ),
        2,
    )

    return {
        "found": True,
        "evaluator_version": EVALUATOR_VERSION,
        "expected_return": expected,
        "actual_return": actual,
        "return_error": return_error,
        "abs_return_error": abs_return_error,
        "expected_downside": expected_downside,
        "actual_drawdown": max_dd,
        "downside_error": downside_error,
        "timing_error": timing_error,
        "scenario_accuracy": round(scenario_accuracy, 4),
        "confidence_accuracy": confidence_accuracy,
        "alpha": alpha,
        "score": score,
        "grade": (
            "A"
            if score >= 85
            else "B"
            if score >= 70
            else "C"
            if score >= 55
            else "D"
            if score >= 40
            else "F"
        ),
        "small_error": abs_return_error <= 0.05,
    }
