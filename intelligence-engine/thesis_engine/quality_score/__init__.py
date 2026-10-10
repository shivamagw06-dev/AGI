"""Thesis quality score, deliberately separate from thesis conviction."""

from __future__ import annotations

import math
from typing import Any


def score_thesis_quality(
    pillars: list[dict[str, Any]],
    contradictions: dict[str, Any],
    *,
    calibration: float,
) -> dict[str, Any]:
    evidence_backed = sum(1 for p in pillars if p.get("evidence_backed"))
    evidence_items = sum(len(p.get("evidence") or []) for p in pillars)
    contradiction_items = len(contradictions.get("major") or [])
    missing_items = len(contradictions.get("missing_evidence") or [])

    evidence = min(1.0, evidence_items / 14.0)
    contradiction_handling = min(1.0, contradiction_items / 4.0)
    coverage = evidence_backed / max(len(pillars), 1)
    calibration_score = max(0.0, min(1.0, float(calibration)))
    completeness = max(0.0, min(1.0, 1.0 - missing_items / 10.0))
    coherence = max(
        0.0,
        min(1.0, 1.0 - len(contradictions.get("outstanding_questions") or []) / 12.0),
    )

    dimensions = {
        "evidence": round(evidence, 4),
        "contradictions": round(contradiction_handling, 4),
        "coverage": round(coverage, 4),
        "calibration": round(calibration_score, 4),
        "completeness": round(completeness, 4),
        "coherence": round(coherence, 4),
    }
    # Weighted geometric mean prevents one weak dimension being hidden by averages.
    weights = {
        "evidence": 0.22,
        "contradictions": 0.18,
        "coverage": 0.2,
        "calibration": 0.16,
        "completeness": 0.12,
        "coherence": 0.12,
    }
    overall = math.exp(
        sum(weights[k] * math.log(max(dimensions[k], 0.01)) for k in dimensions)
    )
    return {
        "overall": round(overall, 4),
        "overall_pct": round(overall * 100),
        "dimensions": dimensions,
        "dimension_pct": {k: round(v * 100) for k, v in dimensions.items()},
        "weights": weights,
        "band": "High" if overall >= 0.78 else "Moderate" if overall >= 0.58 else "Low",
        "separate_from_conviction": True,
    }
