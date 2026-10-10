"""Forecast quality scoring from immutable validation records."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import ForecastScore, ForecastValidation


def score_validation(validation: ForecastValidation) -> ForecastScore:
    diff = validation.difference
    expected = validation.expected_outcome
    actual = validation.actual_outcome

    # Scenario accuracy
    if diff.scenario_match:
        scenario_acc = 94
    elif diff.scenario_distance == 1:
        scenario_acc = 62
    else:
        scenario_acc = 28

    # Probability calibration (single-shot proxy: modal mass vs hit)
    modal = expected.modal_scenario
    modal_p = float((expected.probability_distribution or {}).get(modal) or 50)
    hit = 100.0 if diff.scenario_match else 0.0
    # Closer predicted mass to outcome → higher score; overconfident misses penalized
    gap = abs(modal_p - hit)
    if diff.scenario_match:
        # Well-calibrated if modal wasn't extreme certainty on a hit
        prob_cal = int(round(max(55, 100 - gap * 0.35)))
    else:
        # Penalize high probability on wrong modal
        prob_cal = int(round(max(20, 85 - modal_p * 0.7)))

    # Catalyst accuracy
    hit_rate = float(diff.catalyst_hit_rate or 0.0)
    catalyst_acc = int(round(40 + 55 * hit_rate))

    # Timing
    if diff.timing_match:
        timing_acc = 86 if actual.timing_realized == "on_time" else 78
    else:
        timing_acc = 42 if actual.timing_realized == "unknown" else 48

    # Confidence calibration — high confidence should correlate with correctness
    conf = int(expected.confidence_pct or 50)
    correctish = validation.validation_status in {"Validated", "Partially Correct"}
    if correctish and conf >= 70:
        conf_cal = 95
    elif correctish and conf >= 50:
        conf_cal = 88
    elif not correctish and conf >= 80:
        conf_cal = 40  # overconfident miss
    elif not correctish and conf >= 60:
        conf_cal = 58
    else:
        conf_cal = 72

    overall = int(
        round(
            0.30 * scenario_acc
            + 0.20 * prob_cal
            + 0.15 * catalyst_acc
            + 0.15 * timing_acc
            + 0.20 * conf_cal
        )
    )
    overall = max(15, min(99, overall))

    return ForecastScore(
        overall=overall,
        scenario_accuracy=scenario_acc,
        probability_calibration=prob_cal,
        catalyst_accuracy=catalyst_acc,
        timing_accuracy=timing_acc,
        confidence_calibration=conf_cal,
        components={
            "validation_status": validation.validation_status,
            "metric_agreement_pct": diff.metric_agreement_pct,
            "modal_probability_pct": modal_p,
            "rule": "deterministic_weighted_blend",
        },
    )


def aggregate_scores(validations: list[ForecastValidation]) -> dict[str, Any]:
    if not validations:
        return {
            "n": 0,
            "overall": 0,
            "scenario_accuracy": 0,
            "probability_calibration": 0,
            "catalyst_accuracy": 0,
            "timing_accuracy": 0,
            "confidence_calibration": 0,
            "validation_accuracy_pct": 0.0,
        }

    scores = [score_validation(v) for v in validations]
    n = len(scores)
    validated_ok = sum(
        1 for v in validations if v.validation_status in {"Validated", "Partially Correct"}
    )
    return {
        "n": n,
        "overall": int(round(sum(s.overall for s in scores) / n)),
        "scenario_accuracy": int(round(sum(s.scenario_accuracy for s in scores) / n)),
        "probability_calibration": int(round(sum(s.probability_calibration for s in scores) / n)),
        "catalyst_accuracy": int(round(sum(s.catalyst_accuracy for s in scores) / n)),
        "timing_accuracy": int(round(sum(s.timing_accuracy for s in scores) / n)),
        "confidence_calibration": int(round(sum(s.confidence_calibration for s in scores) / n)),
        "validation_accuracy_pct": round(100.0 * validated_ok / n, 2),
        "by_status": _status_counts(validations),
    }


def _status_counts(validations: list[ForecastValidation]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in validations:
        out[v.validation_status] = out.get(v.validation_status, 0) + 1
    return out
