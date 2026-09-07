"""Confidence calibration — meta-confidence in the institutional belief."""

from __future__ import annotations

from typing import Any


def calibrate_confidence(
    *,
    prior: float,
    posterior: float,
    support_count: int,
    contradiction_count: int,
    missing_count: int,
    contribution_count: int,
    historical_calibration: float | None = None,
) -> dict[str, Any]:
    """
    Confidence ≠ belief probability.
    High confidence means the belief is well-evidenced and stable; low means fragile.
    """
    evidence_mass = min(1.0, (support_count + contradiction_count) / 8.0)
    balance = 1.0 - abs(support_count - contradiction_count) / max(support_count + contradiction_count, 1)
    # Extremes with thin evidence → lower confidence
    extremity = abs(posterior - 0.5) * 2
    thin_extreme_penalty = 0.15 * extremity * (1.0 - evidence_mass)
    missing_penalty = min(0.2, 0.04 * missing_count)
    move = abs(posterior - prior)
    instability_penalty = min(0.12, move * 0.25)

    raw = 0.35 + 0.35 * evidence_mass + 0.15 * balance + 0.1 * min(1.0, contribution_count / 6.0)
    raw = raw - thin_extreme_penalty - missing_penalty - instability_penalty

    if historical_calibration is not None:
        # Blend toward historical calibration score
        raw = 0.75 * raw + 0.25 * float(historical_calibration)

    confidence = round(max(0.2, min(0.95, raw)), 4)
    band = (
        "High"
        if confidence >= 0.75
        else "Moderate"
        if confidence >= 0.55
        else "Low"
    )
    return {
        "confidence": confidence,
        "confidence_pct": round(confidence * 100),
        "confidence_band": band,
        "components": {
            "evidence_mass": round(evidence_mass, 4),
            "balance": round(balance, 4),
            "thin_extreme_penalty": round(thin_extreme_penalty, 4),
            "missing_penalty": round(missing_penalty, 4),
            "instability_penalty": round(instability_penalty, 4),
            "historical_blend": historical_calibration,
        },
        "interpretation": (
            f"{band} confidence that the posterior belief is institutionally reliable"
        ),
    }
