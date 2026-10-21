"""Contribution weights by objective — sum to 1.0 over required (+ optional if included)."""

from __future__ import annotations

from typing import Any

# Weights for required specialists (optional get residual / explicit small share)
_WEIGHT_TEMPLATES: dict[str, dict[str, float]] = {
    "Investment Evaluation": {
        "Business": 0.30,
        "Financial": 0.25,
        "Valuation": 0.20,
        "Risk": 0.10,
        "Forecast": 0.10,
        "Portfolio": 0.05,
    },
    "Portfolio Decision": {
        "Portfolio": 0.40,
        "Risk": 0.25,
        "Business": 0.15,
        "Forecast": 0.10,
        "Valuation": 0.10,
    },
    "Peer Comparison": {
        "Business": 0.30,
        "Financial": 0.25,
        "Valuation": 0.25,
        "Sector": 0.20,
    },
    "Historical Analysis": {
        "Valuation": 0.40,
        "Sector": 0.25,
        "Macro": 0.20,
        "Forecast": 0.15,
    },
    "Educational": {
        "Academy": 0.70,
        "Financial": 0.30,
    },
    "Macro Impact": {
        "Macro": 0.40,
        "Sector": 0.25,
        "Forecast": 0.20,
        "Risk": 0.15,
    },
    "Valuation Assessment": {
        "Valuation": 0.55,
        "Financial": 0.30,
        "Sector": 0.10,
        "Macro": 0.05,
    },
    "Risk Assessment": {
        "Risk": 0.45,
        "Financial": 0.30,
        "Macro": 0.15,
        "Portfolio": 0.10,
    },
    "Business Quality Assessment": {
        "Business": 0.55,
        "Management": 0.25,
        "Financial": 0.15,
        "Sector": 0.05,
    },
    "Forecast": {
        "Forecast": 0.50,
        "Financial": 0.30,
        "Macro": 0.20,
    },
}


def assign_weights(
    primary_objective: str | None,
    required: list[str],
    optional: list[str] | None = None,
    *,
    include_optional: bool = False,
) -> dict[str, Any]:
    obj = primary_objective or ""
    template = dict(_WEIGHT_TEMPLATES.get(obj) or {})
    participants = list(required)
    if include_optional:
        for a in optional or []:
            if a not in participants:
                participants.append(a)

    weights: dict[str, float] = {}
    if template:
        # Keep only participating analysts from template
        for a in participants:
            if a in template:
                weights[a] = float(template[a])
        # Drop template keys not participating; redistribute if needed
        missing = [a for a in participants if a not in weights]
        total = sum(weights.values())
        if missing:
            residual = max(0.0, 1.0 - total)
            share = residual / len(missing) if missing else 0.0
            for a in missing:
                weights[a] = round(share, 4) if share > 0 else round(1.0 / len(participants), 4)
            total = sum(weights.values())
        if total > 0 and abs(total - 1.0) > 1e-6:
            weights = {k: round(v / total, 4) for k, v in weights.items()}
            # Fix rounding drift on largest
            drift = round(1.0 - sum(weights.values()), 4)
            if weights:
                top = max(weights, key=weights.get)
                weights[top] = round(weights[top] + drift, 4)
    else:
        n = max(1, len(participants))
        base = round(1.0 / n, 4)
        weights = {a: base for a in participants}
        if weights:
            drift = round(1.0 - sum(weights.values()), 4)
            top = max(weights, key=weights.get)
            weights[top] = round(weights[top] + drift, 4)

    # Optional analysts: informational weight 0 unless include_optional
    optional_weights = {a: 0.0 for a in (optional or []) if a not in weights}

    return {
        "weights": weights,
        "optional_weights": optional_weights,
        "weight_sum": round(sum(weights.values()), 4),
        "map_version": "iar-v1",
    }
