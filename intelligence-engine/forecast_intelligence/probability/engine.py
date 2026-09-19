"""Probability engine — dynamic, evidence-backed, never fixed or deterministic."""

from __future__ import annotations

from typing import Any

from forecast_intelligence.schema import SCENARIO_NAMES


def score_probabilities(
    profile: dict[str, Any],
    *,
    catalysts: dict[str, Any] | None = None,
    uncertainty: dict[str, Any] | None = None,
    causal_soft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assign dynamic scenario probabilities that always sum to 1.0."""
    sector = (profile.get("sector") or "banks").lower()
    # Sector priors (not fixed forever — adjusted by catalysts / uncertainty / causal)
    priors = {
        "banks": {"bull": 0.22, "base": 0.40, "bear": 0.22, "stress": 0.08, "recovery": 0.08},
        "it_services": {"bull": 0.20, "base": 0.42, "bear": 0.22, "stress": 0.08, "recovery": 0.08},
        "fmcg": {"bull": 0.18, "base": 0.44, "bear": 0.22, "stress": 0.07, "recovery": 0.09},
        "metals": {"bull": 0.20, "base": 0.36, "bear": 0.24, "stress": 0.12, "recovery": 0.08},
    }.get(sector, {"bull": 0.20, "base": 0.40, "bear": 0.22, "stress": 0.08, "recovery": 0.10})

    scores = {k: float(v) for k, v in priors.items()}

    # Catalyst tilt
    pos = len((catalysts or {}).get("by_polarity", {}).get("positive") or [])
    neg = len((catalysts or {}).get("by_polarity", {}).get("negative") or [])
    scores["bull"] += 0.02 * pos
    scores["bear"] += 0.02 * neg
    scores["stress"] += 0.01 * max(0, neg - pos)

    # Uncertainty widens tails
    u_score = float((uncertainty or {}).get("uncertainty_score") or 0.35)
    scores["stress"] += 0.05 * u_score
    scores["bull"] -= 0.03 * u_score
    scores["base"] -= 0.02 * u_score

    # Soft causal confidence slightly concentrates mass on base if high
    cig_conf = float((causal_soft or {}).get("confidence") or 0.6)
    scores["base"] += 0.04 * cig_conf
    scores["stress"] -= 0.02 * cig_conf

    # Floor and renormalise — never deterministic (no 100%)
    for k in SCENARIO_NAMES:
        scores[k] = max(0.04, scores.get(k, 0.04))
    total = sum(scores.values())
    probs = {k: round(scores[k] / total, 3) for k in SCENARIO_NAMES}
    # Fix rounding drift on base
    drift = round(1.0 - sum(probs.values()), 3)
    probs["base"] = round(probs["base"] + drift, 3)

    coverage = 0.55 + 0.1 * min(4, len(profile.get("analogues") or [])) + 0.05 * min(
        5, len((catalysts or {}).get("items") or [])
    )
    coverage = min(0.92, coverage)

    return {
        "distribution": probs,
        "most_likely": max(probs, key=probs.get),
        "most_likely_probability": probs[max(probs, key=probs.get)],
        "dynamic": True,
        "deterministic": False,
        "evidence_coverage": round(coverage, 3),
        "historical_analogue_count": len(profile.get("analogues") or []),
        "unknowns": (uncertainty or {}).get("known_unknowns") or [],
        "rule": "Probability is dynamic and evidence-backed — never a single price path",
    }
