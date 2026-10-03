"""Confidence validator — component + overall readiness confidence."""

from __future__ import annotations

from typing import Any

from validation_engine.schema import READINESS_WEIGHTS


def validate_confidence(
    *,
    components: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    scores = {}
    for key, weight in READINESS_WEIGHTS.items():
        row = components.get(key) or {}
        scores[key] = float(row.get("score") or 0.0)

    overall = sum(scores[k] * READINESS_WEIGHTS[k] for k in READINESS_WEIGHTS)
    return {
        "component_scores": {k: round(v, 4) for k, v in scores.items()},
        "weights": dict(READINESS_WEIGHTS),
        "overall_readiness": round(overall, 4),
        "confidence": round(overall, 4),
    }
