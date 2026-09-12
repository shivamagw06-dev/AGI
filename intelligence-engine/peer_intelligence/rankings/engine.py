"""Ranking engine — company ranks across quality dimensions."""

from __future__ import annotations

from typing import Any

from peer_intelligence.percentile.engine import LOWER_BETTER, percentiles_for
from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker

DIMENSION_METRICS = {
    "margins": ["Operating_Margin", "EBIT_Margin", "NIM", "Gross_Margin", "Net_Margin"],
    "returns": ["ROE", "ROA", "ROIC"],
    "growth": ["Revenue_Growth", "Deposit_Growth", "Loan_Growth"],
    "capital": ["CET1", "Capital_Ratio"],
    "asset_quality": ["GNPA", "NNPA", "Credit_Cost", "Provision_Coverage"],
    "funding": ["CASA", "Cost_of_Funds", "Deposit_Beta"],
    "cash": ["Cash_Conversion", "Free_Cash_Flow", "FCF_Conversion"],
    "valuation": ["PE", "PB", "EV_EBITDA"],
    "business_quality": ["CASA", "ROIC", "Unit_Economics", "Take_Rate", "Retention"],
    "financial_quality": ["ROE", "EBIT_Margin", "Cash_Conversion", "CET1"],
}


def rankings_for(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    pct = percentiles_for(t, universe="direct")
    if not pct.get("found"):
        return {"ticker": t, "found": False, "rankings": {}}

    by_metric = {p["metric"]: p for p in pct.get("percentiles") or []}
    rankings: dict[str, Any] = {}
    for dim, metrics in DIMENSION_METRICS.items():
        hits = [by_metric[m] for m in metrics if m in by_metric]
        if not hits:
            continue
        avg_pct = round(sum(h["percentile"] for h in hits) / len(hits), 1)
        best = min(hits, key=lambda h: h["rank"] or 99)
        rankings[dim] = {
            "percentile": avg_pct,
            "best_metric": best["metric"],
            "best_rank": best["rank"],
            "metrics": hits,
        }

    # flat metric ranks
    flat = [
        {
            "metric": p["metric"],
            "rank": p["rank"],
            "n": p["n"],
            "value": p["value"],
            "percentile": p["percentile"],
            "lower_better": p["metric"] in LOWER_BETTER,
        }
        for p in pct.get("percentiles") or []
    ]
    flat.sort(key=lambda r: r["rank"] or 99)
    return {
        "ticker": t,
        "found": True,
        "sector": pack["sector"] if pack else None,
        "dimensions": rankings,
        "metric_ranks": flat,
        "peer_universe": pack.get("direct_universe") if pack else [],
    }
