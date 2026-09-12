"""Hypothesis ranking — highest expected impact first."""

from __future__ import annotations

from typing import Any

from hypothesis_engine.taxonomy import DEFAULT_IMPACT_WEIGHTS


def rank_hypotheses(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    type_impact: dict[str, float] = {}
    for h in hypotheses:
        t = str(h.get("type") or "Business")
        impact = float(DEFAULT_IMPACT_WEIGHTS.get(t, 0.05))
        conf = float(h.get("confidence") or 0.5)
        # expected impact ≈ type weight × confidence × quality
        quality = 1.0 if h.get("quality_compliant") else 0.5
        score = impact * (0.55 + 0.45 * conf) * quality
        scored.append({**h, "impact_weight": impact, "rank_score": round(score, 4)})
        type_impact[t] = type_impact.get(t, 0.0) + score

    scored.sort(key=lambda x: (-x["rank_score"], -float(x.get("confidence") or 0)))
    for i, h in enumerate(scored, start=1):
        h["priority"] = i

    # Normalise type impacts for display
    total = sum(type_impact.values()) or 1.0
    ranking_by_type = {
        k: round(v / total, 4)
        for k, v in sorted(type_impact.items(), key=lambda kv: -kv[1])
    }
    return {
        "hypotheses": scored,
        "ranking_by_type": ranking_by_type,
        "top_hypothesis_id": scored[0]["id"] if scored else None,
    }
