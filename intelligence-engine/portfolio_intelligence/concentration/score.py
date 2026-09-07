"""Concentration engine — single name / sector / theme risk."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def concentration_score(
    holdings: list[dict[str, Any]],
    *,
    single_name_limit: float,
    sector_limits: dict[str, float] | None,
) -> dict[str, Any]:
    by_ticker = sorted(
        ((str(h.get("ticker")), float(h.get("weight") or 0)) for h in holdings),
        key=lambda x: -x[1],
    )
    top = by_ticker[0] if by_ticker else ("", 0.0)
    sector_w: dict[str, float] = defaultdict(float)
    for h in holdings:
        sector_w[str(h.get("sector") or "other")] += float(h.get("weight") or 0)
    top_sector = max(sector_w.items(), key=lambda kv: kv[1]) if sector_w else ("", 0.0)

    name_breach = top[1] > float(single_name_limit or 0.12)
    sector_breaches = [
        s for s, w in sector_w.items() if sector_limits and s in sector_limits and w > sector_limits[s]
    ]

    # Higher score = less concentrated (safer)
    score = 85.0
    if name_breach:
        score -= 25
    score -= min(30.0, max(0.0, (top[1] - 0.08) * 200))
    score -= min(20.0, max(0.0, (top_sector[1] - 0.25) * 100))
    score -= 10.0 * len(sector_breaches)
    score = max(0.0, min(100.0, score))

    return {
        "concentration": round(score, 1),
        "top_holding": {"ticker": top[0], "weight": round(top[1], 4)},
        "top_sector": {"sector": top_sector[0], "weight": round(top_sector[1], 4)},
        "single_name_limit": single_name_limit,
        "single_name_breach": name_breach,
        "sector_breaches": sector_breaches,
        "risks": {
            "single_stock": top[0],
            "sector": top_sector[0],
            "theme": "private_bank_cluster" if sector_w.get("banks", 0) >= 0.25 else "balanced",
        },
    }
