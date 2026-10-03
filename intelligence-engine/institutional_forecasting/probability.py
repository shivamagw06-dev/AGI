"""Probability engine — scenario probability is always explicit, never implied."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping

from institutional_forecasting.schema import DEFAULT_PROBABILITIES, SCENARIO_NAMES


def normalize_probabilities(raw: Mapping[str, float] | None) -> Dict[str, float]:
    """Normalize a probability map so values are non-negative and sum to 1.0."""
    body = {str(k).strip().lower(): float(v) for k, v in dict(raw or {}).items()}
    body = {k: max(0.0, v) for k, v in body.items() if k}
    total = sum(body.values())
    if total <= 0:
        return dict(DEFAULT_PROBABILITIES)
    return {k: v / total for k, v in body.items()}


def probability_for(scenario_name: str, distribution: Mapping[str, float] | None = None) -> float:
    name = str(scenario_name or "").strip().lower()
    dist = normalize_probabilities(distribution) if distribution else dict(DEFAULT_PROBABILITIES)
    if name in dist:
        return float(dist[name])
    # Stress / optimistic / custom — explicit residual or fixed institutional defaults
    if name == "stress":
        return float(dist.get("stress", 0.10 if "stress" not in (distribution or {}) else dist["stress"]))
    if name == "optimistic":
        return float(dist.get("optimistic", 0.10))
    if name == "custom":
        return float(dist.get("custom", 0.0))
    return float(dist.get(name, 0.0))


def standard_distribution(
    *,
    include_stress: bool = False,
    include_optimistic: bool = False,
) -> Dict[str, float]:
    """Explicit institutional default distribution."""
    base = dict(DEFAULT_PROBABILITIES)  # 0.50 / 0.25 / 0.25
    if include_stress and include_optimistic:
        # Reallocate: base 0.40, bull 0.20, bear 0.20, stress 0.10, optimistic 0.10
        return normalize_probabilities(
            {"base": 0.40, "bull": 0.20, "bear": 0.20, "stress": 0.10, "optimistic": 0.10}
        )
    if include_stress:
        return normalize_probabilities({"base": 0.45, "bull": 0.225, "bear": 0.225, "stress": 0.10})
    if include_optimistic:
        return normalize_probabilities(
            {"base": 0.45, "bull": 0.225, "bear": 0.225, "optimistic": 0.10}
        )
    return base


def validate_probability(value: float) -> list[str]:
    errors: list[str] = []
    try:
        p = float(value)
    except (TypeError, ValueError):
        return ["scenario without probability"]
    if p < 0.0 or p > 1.0:
        errors.append("scenario probability must be between 0 and 1")
    return errors


def known_scenario_name(name: str) -> bool:
    return str(name or "").strip().lower() in SCENARIO_NAMES
