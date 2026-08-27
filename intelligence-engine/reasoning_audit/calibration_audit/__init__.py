"""Confidence calibration audit."""

from __future__ import annotations

from typing import Any


def audit_calibration(trace: dict[str, Any]) -> dict[str, Any]:
    data = trace["stage_data"]
    belief = data.get("Belief Update") or {}
    testing = data.get("Testing") or {}
    beliefs = belief.get("beliefs") or []
    tested = {
        str(h.get("id") or h.get("hypothesis_id")): h
        for h in testing.get("tested_hypotheses") or []
        if isinstance(h, dict)
    }
    rows = []
    for item in beliefs:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("hypothesis_id") or item.get("id"))
        probability = float(
            item.get("posterior_belief")
            or item.get("updated_probability")
            or 0.5
        )
        confidence = float(item.get("confidence") or 0.5)
        test = tested.get(hid) or {}
        support = float(test.get("support_score") or 50) / 100
        contradiction = float(test.get("contradiction_score") or 50) / 100
        evidence_strength = max(
            0.0, min(1.0, 0.5 + 0.5 * (support - contradiction))
        )
        calibration = item.get("calibration") or {}
        historical = (
            (calibration.get("components") or {}).get("historical_blend")
            if isinstance(calibration, dict)
            else None
        )
        forecast = item.get("forecast_calibration")
        bounded = (
            0 <= probability <= 1
            and 0 <= confidence <= 1
            and 0 <= evidence_strength <= 1
        )
        gap = abs(probability - confidence)
        calibrated = bounded and gap <= 0.45
        rows.append(
            {
                "hypothesis_id": hid,
                "belief_probability": round(probability, 4),
                "confidence": round(confidence, 4),
                "evidence_strength": round(evidence_strength, 4),
                "historical_calibration": historical,
                "forecast_calibration": forecast,
                "probability_confidence_gap": round(gap, 4),
                "calibrated": calibrated,
            }
        )
    if not rows:
        return {
            "score": 0.0,
            "score_pct": 0,
            "passed": False,
            "rows": [],
            "issues": ["No belief probabilities available"],
        }
    calibrated_count = sum(1 for row in rows if row["calibrated"])
    score = calibrated_count / len(rows)
    observations = []
    if any(row["historical_calibration"] is None for row in rows):
        observations.append(
            "Historical calibration unavailable for some beliefs"
        )
    if any(row["forecast_calibration"] is None for row in rows):
        observations.append(
            "Forecast calibration pending outcome realization"
        )
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": score == 1.0,
        "rows": rows,
        "calibrated_count": calibrated_count,
        "belief_count": len(rows),
        "observations": observations,
        "issues": [
            row for row in rows if not row["calibrated"]
        ],
    }
