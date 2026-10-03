"""CCI-01 Similarity Engine — ranked peers by sector / model / macro exposure."""

from __future__ import annotations

from typing import Any

from institutional_cross_company.models import SimilarityHit
from institutional_cross_company.relationship_registry import ecosystem_for, peers_of
from institutional_cross_company.schema import ECOSYSTEMS


def similar_companies(ticker: str, *, limit: int = 8) -> list[SimilarityHit]:
    t = str(ticker or "").upper().strip()
    hit = ecosystem_for(t)
    scores: dict[str, list[str]] = {}

    if hit:
        _, eco = hit
        for peer in peers_of(t):
            reasons = ["same_sector", "same_industry", "peer_group"]
            if set(eco.get("macro") or ()):
                reasons.append("shared_macro_exposure")
            scores[peer] = reasons

    # Soft valuation / quality placeholders — structural similarity only (no invented ratings)
    for eco in ECOSYSTEMS.values():
        members = [str(m).upper() for m in (eco.get("members") or ())]
        if t not in members:
            continue
        for peer in members:
            if peer == t:
                continue
            scores.setdefault(peer, []).append("financial_quality_cohort")

    ranked: list[SimilarityHit] = []
    for peer, reasons in scores.items():
        uniq = tuple(dict.fromkeys(reasons))
        score = min(0.99, 0.45 + 0.12 * len(uniq))
        ranked.append(SimilarityHit(ticker=peer, score=score, reasons=uniq))
    ranked.sort(key=lambda x: (-x.score, x.ticker))
    return ranked[:limit]


def similarity_pack(ticker: str) -> dict[str, Any]:
    hits = similar_companies(ticker)
    return {
        "ticker": str(ticker or "").upper(),
        "similar": [h.to_dict() for h in hits],
        "count": len(hits),
        "dimensions": ["sector", "business_model", "macro_exposure", "financial_quality_cohort"],
        "generates_recommendations": False,
    }
