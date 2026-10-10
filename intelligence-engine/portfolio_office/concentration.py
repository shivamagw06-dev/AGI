"""Concentration metrics from holding weights."""

from __future__ import annotations

from typing import Any, Mapping


def compute_concentration(portfolio: Mapping[str, Any]) -> dict[str, Any]:
    holdings = sorted(
        [dict(h) for h in (portfolio.get("holdings") or [])],
        key=lambda h: float(h.get("weight") or 0.0),
        reverse=True,
    )
    weights = [float(h.get("weight") or 0.0) for h in holdings]
    n = len(holdings)
    largest = holdings[0] if holdings else None
    top5 = sum(weights[:5])
    top10 = sum(weights[:10])
    # HHI on equity weights (not including cash) — standard concentration measure
    hhi = sum(w * w for w in weights)
    return {
        "schema": "po01.concentration.v1",
        "number_of_holdings": n,
        "largest_position": {
            "ticker": (largest or {}).get("ticker"),
            "weight": float((largest or {}).get("weight") or 0.0),
            "company": (largest or {}).get("company"),
        }
        if largest
        else None,
        "top_5_weight": top5,
        "top_10_weight": top10,
        "hhi": hhi,
        "note": "HHI uses holding weights only (cash excluded). Not a risk model.",
    }
