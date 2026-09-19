"""Liquidity engine — days-to-exit proxies (institutional ADV priors)."""

from __future__ import annotations

from typing import Any

# Illustrative ADV category → days to exit  for a full book slice
_ADV_DAYS = {
    "large": 2.0,
    "mid": 8.0,
    "small": 25.0,
}


def liquidity_score(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    weighted_days = 0.0
    tw = 0.0
    for h in holdings:
        w = float(h.get("weight") or 0)
        mcap = str(h.get("market_cap") or "large").lower()
        days = _ADV_DAYS.get(mcap, 10.0)
        rows.append(
            {
                "ticker": h.get("ticker"),
                "weight": round(w, 4),
                "market_cap": mcap,
                "days_to_exit_proxy": days,
            }
        )
        weighted_days += w * days
        tw += w
    avg_days = weighted_days / tw if tw else 0.0
    score = max(0.0, min(100.0, 100.0 - (avg_days - 2.0) * 4.0))
    return {
        "liquidity": round(score, 1),
        "portfolio_days_to_exit": round(avg_days, 2),
        "positions": rows,
        "label": "strong" if avg_days <= 5 else "adequate" if avg_days <= 12 else "constrained",
        "evidence_note": "Days-to-exit uses market-cap liquidity priors until live ADV series wired",
    }
