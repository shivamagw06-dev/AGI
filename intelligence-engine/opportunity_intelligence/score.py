"""Opportunity score + research priority — transparent contributions."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.schema import DIMENSION_WEIGHTS, RESEARCH_PRIORITIES, TECHNICAL_SOFT_CAP
from opportunity_intelligence.util import as_float, clamp, round1


def compose_score(
    dimensions: dict[str, Any],
    *,
    blockers: list[dict[str, Any]],
    technical: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contributions: list[dict[str, Any]] = []
    weighted = 0.0
    weight_sum = 0.0

    for key, weight in DIMENSION_WEIGHTS.items():
        dim = dimensions.get(key) or {}
        raw = as_float(dim.get("score"))
        if raw is None or not dim.get("available"):
            # Missing dimension: neutral 50 with half weight (transparent)
            raw = 50.0
            effective_w = weight * 0.5
            available = False
        else:
            effective_w = weight
            available = True
        contrib = raw * effective_w
        weighted += contrib
        weight_sum += effective_w
        contributions.append(
            {
                "dimension": key,
                "raw_score": round1(raw),
                "weight": weight,
                "effective_weight": round(effective_w, 4),
                "contribution": round1(contrib),
                "available": available,
                "signals": (dim.get("signals") or [])[:4],
            }
        )

    base = weighted / weight_sum if weight_sum else 50.0

    # Technical soft bump only
    tech_adj = 0.0
    tech_score = as_float((technical or {}).get("score"))
    if tech_score is not None and (technical or {}).get("available"):
        tech_adj = clamp((tech_score - 50.0) * 0.12, -TECHNICAL_SOFT_CAP, TECHNICAL_SOFT_CAP)
        contributions.append(
            {
                "dimension": "technical_context",
                "raw_score": round1(tech_score),
                "weight": 0.0,
                "effective_weight": 0.0,
                "contribution": round1(tech_adj),
                "available": True,
                "signals": ((technical or {}).get("signals") or [])[:3],
                "note": "supporting_only_soft_cap",
            }
        )

    penalty = sum(float(b.get("score_penalty") or 0) for b in blockers)
    # Cap penalty so blockers never fully zero a rich evidence pack
    penalty = min(35.0, penalty)
    final = clamp(base + tech_adj - penalty)

    # Sort contributions by absolute impact for explainability
    ranked = sorted(
        contributions,
        key=lambda c: (-abs(float(c.get("contribution") or 0)), c.get("dimension") or ""),
    )

    return {
        "score": round1(final),
        "base_score": round1(base),
        "technical_adjustment": round1(tech_adj),
        "blocker_penalty": round1(penalty),
        "contributions": contributions,
        "top_contributors": ranked[:5],
        "weights": dict(DIMENSION_WEIGHTS),
    }


def research_priority(score: float, blockers: list[dict[str, Any]]) -> str:
    high_blockers = sum(1 for b in blockers if b.get("severity") == "High")
    s = float(score)
    if s >= 80 and high_blockers == 0:
        return "Critical"
    if s >= 80 and high_blockers >= 1:
        return "High"
    if s >= 65:
        return "High"
    if s >= 50:
        return "Medium"
    if s >= 35:
        return "Low"
    return "Monitor"


def priority_rank(priority: str) -> int:
    try:
        return RESEARCH_PRIORITIES.index(priority)
    except ValueError:
        return len(RESEARCH_PRIORITIES)


def explain_score_moves(
    *,
    score_pack: dict[str, Any],
    blockers: list[dict[str, Any]],
    dimensions: dict[str, Any],
) -> dict[str, Any]:
    top = score_pack.get("top_contributors") or []
    increased = [
        f"{c['dimension']} contributed {c.get('contribution')} (raw {c.get('raw_score')})"
        for c in top
        if float(c.get("raw_score") or 50) >= 55
    ]
    decreased = [
        f"{c['dimension']} dragged score (raw {c.get('raw_score')})"
        for c in top
        if float(c.get("raw_score") or 50) < 45
    ]
    decreased.extend([f"Blocker: {b.get('title')}" for b in blockers[:5]])

    improve = []
    weaken = []
    for key, dim in dimensions.items():
        sc = as_float(dim.get("score"))
        if sc is None:
            continue
        if sc < 55:
            improve.append(f"Raise {key.replace('_', ' ')} via stronger evidence (now {sc:.0f})")
        if sc >= 70:
            weaken.append(f"Reversal in {key.replace('_', ' ')} would reduce opportunity (now {sc:.0f})")
    for b in blockers[:4]:
        improve.append(f"Resolve blocker: {b.get('title')}")

    return {
        "why_score_increased": increased[:6] or ["No strong positive dimension dominance"],
        "why_score_decreased": decreased[:6] or ["No material drag identified"],
        "most_contributing_evidence": [
            s for c in top for s in (c.get("signals") or [])[:1]
        ][:6],
        "conviction_reducing_evidence": [b.get("detail") or b.get("title") for b in blockers[:6]],
        "what_would_improve_profile": improve[:6],
        "what_would_weaken_profile": weaken[:6],
    }
