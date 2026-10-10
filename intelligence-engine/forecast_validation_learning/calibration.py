"""Probability and confidence calibration trends over completed validations."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import CalibrationPoint, ForecastValidation


def _bucket_label(pct: float) -> str:
    if pct < 20:
        return "0-19"
    if pct < 40:
        return "20-39"
    if pct < 60:
        return "40-59"
    if pct < 80:
        return "60-79"
    return "80-100"


def probability_calibration(validations: list[ForecastValidation]) -> dict[str, Any]:
    """Compare predicted scenario probabilities with realized frequencies."""
    # Track per-scenario: when we assigned probability mass in a bucket, did it occur?
    # Simpler institutional view: for each scenario type, average predicted vs occurrence rate.
    scenarios = ("Bull", "Base", "Bear")
    predicted_sum = {s: 0.0 for s in scenarios}
    occurred = {s: 0 for s in scenarios}
    n = 0
    points: list[CalibrationPoint] = []

    # Bucket by predicted modal probability
    buckets: dict[str, list[tuple[float, bool]]] = {}

    for v in validations:
        if v.validation_status == "Indeterminate":
            continue
        n += 1
        dist = v.expected_outcome.probability_distribution or {}
        realized = v.actual_outcome.realized_scenario
        for s in scenarios:
            predicted_sum[s] += float(dist.get(s) or 0)
            if realized == s:
                occurred[s] += 1
        modal = v.expected_outcome.modal_scenario
        modal_p = float(dist.get(modal) or 0)
        buckets.setdefault(_bucket_label(modal_p), []).append((modal_p, realized == modal))

    scenario_rows = []
    for s in scenarios:
        pred = round(predicted_sum[s] / n, 2) if n else 0.0
        occ = round(100.0 * occurred[s] / n, 2) if n else 0.0
        gap = round(occ - pred, 2)
        note = ""
        if s == "Bull" and gap >= 15:
            note = "Bull probability calibration requires review."
        elif s == "Bull" and gap <= -15:
            note = "Bull scenarios overweighted relative to outcomes."
        scenario_rows.append(
            {
                "scenario": s,
                "predicted_avg_pct": pred,
                "occurred_pct": occ,
                "gap_pct": gap,
                "note": note,
            }
        )
        points.append(
            CalibrationPoint(
                bucket=f"scenario:{s}",
                predicted_pct=pred,
                occurred_pct=occ,
                n=n,
                gap_pct=gap,
                note=note,
            )
        )

    bucket_rows = []
    for label, rows in sorted(buckets.items()):
        if not rows:
            continue
        pred = round(sum(p for p, _ in rows) / len(rows), 2)
        occ = round(100.0 * sum(1 for _, hit in rows if hit) / len(rows), 2)
        bucket_rows.append(
            CalibrationPoint(
                bucket=f"modal_prob:{label}",
                predicted_pct=pred,
                occurred_pct=occ,
                n=len(rows),
                gap_pct=round(occ - pred, 2),
                note="Reliability-style bucket for modal scenario hits.",
            ).model_dump(mode="json")
        )

    alerts = [r["note"] for r in scenario_rows if r["note"]]
    return {
        "n": n,
        "by_scenario": scenario_rows,
        "modal_probability_buckets": bucket_rows,
        "points": [p.model_dump(mode="json") for p in points],
        "alerts": alerts,
        "history_rewritten": False,
    }


def confidence_calibration(validations: list[ForecastValidation]) -> dict[str, Any]:
    """High confidence should correlate with validated / partially correct outcomes."""
    bands = {
        "low_<50": [],
        "medium_50_74": [],
        "high_75_plus": [],
    }
    for v in validations:
        if v.validation_status == "Indeterminate":
            continue
        conf = int(v.expected_outcome.confidence_pct or 0)
        ok = v.validation_status in {"Validated", "Partially Correct"}
        if conf < 50:
            bands["low_<50"].append(ok)
        elif conf < 75:
            bands["medium_50_74"].append(ok)
        else:
            bands["high_75_plus"].append(ok)

    rows = []
    for label, hits in bands.items():
        n = len(hits)
        rate = round(100.0 * sum(1 for h in hits if h) / n, 2) if n else 0.0
        rows.append(
            {
                "confidence_band": label,
                "n": n,
                "correct_or_partial_pct": rate,
            }
        )

    overconfident = 0
    for v in validations:
        conf = int(v.expected_outcome.confidence_pct or 0)
        if conf >= 75 and v.validation_status == "Incorrect":
            overconfident += 1

    alert = None
    if overconfident >= 2:
        alert = "Confidence calibration requires review — high confidence paired with Incorrect outcomes."

    return {
        "bands": rows,
        "overconfident_incorrect": overconfident,
        "alerts": [alert] if alert else [],
        "history_rewritten": False,
    }


def calibration_report(validations: list[ForecastValidation]) -> dict[str, Any]:
    return {
        "probability": probability_calibration(validations),
        "confidence": confidence_calibration(validations),
        "tracked_over_time": True,
        "process_improvement_only": True,
    }
