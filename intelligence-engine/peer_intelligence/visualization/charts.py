"""Visualization data contracts for admin / research writer (no UI redesign)."""

from __future__ import annotations

from typing import Any

from peer_intelligence.historical.series import history_for
from peer_intelligence.percentile.engine import percentiles_for
from peer_intelligence.rankings.engine import rankings_for
from peer_intelligence.resolver.resolve import resolve_peers
from peer_intelligence.trends.engine import trends_for


def visualization_pack(ticker: str) -> dict[str, Any]:
    t = ticker
    resolved = resolve_peers(t)
    pct = percentiles_for(t)
    ranks = rankings_for(t)
    hist = history_for(t)
    trends = trends_for(t)
    return {
        "ticker": resolved.get("ticker") or t,
        "peer_matrix": {
            "direct": [p.get("ticker") for p in resolved.get("direct") or []],
            "global": [p.get("ticker") for p in resolved.get("global_leaders") or []],
        },
        "percentile_chart": [
            {"metric": p["metric"], "percentile": p["percentile"], "rank": p["rank"]}
            for p in pct.get("percentiles") or []
        ],
        "historical_ranking": ranks.get("metric_ranks") or [],
        "trend_dashboard": trends.get("trends") or [],
        "history_series": [
            {"metric": s["metric"], "points": s.get("points")} for s in hist.get("series") or []
        ],
        "note": "Data contracts only — rendered by existing admin soft HTML / RW tables",
    }
