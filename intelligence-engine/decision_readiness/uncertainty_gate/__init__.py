"""Confidence and residual uncertainty readiness."""

from __future__ import annotations

from typing import Any


def evaluate_uncertainty(
    thesis: dict[str, Any],
    debate: dict[str, Any],
    belief_package: dict[str, Any] | None = None,
) -> dict[str, Any]:
    belief_package = belief_package or {}
    thesis_confidence = float(thesis.get("confidence") or 0.5)
    consensus_confidence = float(
        (debate.get("consensus") or {}).get("confidence") or 0.5
    )
    quality = float((thesis.get("quality") or {}).get("overall") or 0.55)
    pressure = float((thesis.get("pressure_gauge") or {}).get("score") or 35) / 100
    beliefs = (
        belief_package.get("beliefs")
        or (belief_package.get("institutional_belief_package") or {}).get("beliefs")
        or []
    )
    belief_confidence = (
        sum(float(b.get("confidence") or 0.5) for b in beliefs)
        / len(beliefs)
        if beliefs
        else thesis_confidence
    )
    confidence = (
        0.35 * thesis_confidence
        + 0.25 * consensus_confidence
        + 0.20 * quality
        + 0.20 * belief_confidence
    )
    uncertainty = max(
        0.0, min(1.0, 1.0 - confidence + 0.2 * pressure)
    )
    return {
        "dimension": "Confidence",
        "score": round(confidence, 4),
        "score_pct": round(confidence * 100),
        "passed": confidence >= 0.65 and uncertainty <= 0.45,
        "confidence": round(confidence, 4),
        "confidence_pct": round(confidence * 100),
        "uncertainty": round(uncertainty, 4),
        "uncertainty_pct": round(uncertainty * 100),
        "components": {
            "thesis_confidence": round(thesis_confidence, 4),
            "consensus_confidence": round(consensus_confidence, 4),
            "thesis_quality": round(quality, 4),
            "belief_confidence": round(belief_confidence, 4),
            "thesis_pressure": round(pressure, 4),
        },
    }
