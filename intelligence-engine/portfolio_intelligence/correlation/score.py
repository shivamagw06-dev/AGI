"""Correlation / hidden concentration — sector-style proxy matrix (V1)."""

from __future__ import annotations

from typing import Any

# Institutional prior correlations by sector pair (illustrative, evidence-tagged as prior)
_SECTOR_CORR = {
    ("banks", "banks"): 0.85,
    ("banks", "it_services"): 0.35,
    ("banks", "fmcg"): 0.25,
    ("it_services", "it_services"): 0.80,
    ("it_services", "fmcg"): 0.20,
    ("fmcg", "fmcg"): 0.70,
    ("telecom", "banks"): 0.40,
    ("consumer_internet", "it_services"): 0.45,
    ("energy_conglomerate", "banks"): 0.50,
}


def _corr(a: str, b: str) -> float:
    if a == b:
        return _SECTOR_CORR.get((a, a), 0.65)
    key = tuple(sorted((a, b)))
    # try both orders in map
    return (
        _SECTOR_CORR.get((a, b))
        or _SECTOR_CORR.get((b, a))
        or _SECTOR_CORR.get(key)
        or 0.35
    )


def correlation_analysis(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    tickers = [str(h.get("ticker")) for h in holdings]
    sectors = {str(h.get("ticker")): str(h.get("sector") or "other") for h in holdings}
    weights = {str(h.get("ticker")): float(h.get("weight") or 0) for h in holdings}

    # Average pairwise correlation weighted
    pairs = []
    num = den = 0.0
    for i, ti in enumerate(tickers):
        for tj in tickers[i + 1 :]:
            c = _corr(sectors[ti], sectors[tj])
            w = weights[ti] * weights[tj]
            num += c * w
            den += w
            pairs.append({"a": ti, "b": tj, "corr": round(c, 2), "sectors": [sectors[ti], sectors[tj]]})
    avg = num / den if den else 0.5

    # Hidden concentration: high weight in highly correlated cluster
    bank_w = sum(weights[t] for t in tickers if sectors[t] == "banks")
    hidden = []
    if bank_w >= 0.22:
        hidden.append(
            {
                "cluster": "private_banks",
                "weight": round(bank_w, 4),
                "note": "High intra-sector correlation — diversification may be overstated by name count",
            }
        )

    score = max(0.0, min(100.0, 100.0 - avg * 80.0))
    return {
        "avg_pairwise_correlation": round(avg, 3),
        "correlation_quality": round(score, 1),  # higher = less correlated = better diversifier geometry
        "hidden_concentration": hidden,
        "sample_pairs": sorted(pairs, key=lambda p: -p["corr"])[:8],
        "method": "sector_prior_matrix_v1",
        "evidence_note": "Pairwise correlations use institutional sector priors until holding-level returns series ingested",
    }
