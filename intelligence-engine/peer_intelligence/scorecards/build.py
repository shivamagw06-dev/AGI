"""Peer scorecards for Committee / CIO / Research Writer."""

from __future__ import annotations

from typing import Any

from peer_intelligence.benchmarking.engine import benchmarks_for
from peer_intelligence.commentary.engine import commentary_for
from peer_intelligence.confidence.score import score_comparison
from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker
from peer_intelligence.rankings.engine import rankings_for
from peer_intelligence.resolver.resolve import resolve_peers


def scorecard(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    resolved = resolve_peers(t)
    bench = benchmarks_for(t)
    ranks = rankings_for(t)
    comment = commentary_for(t)
    conf = score_comparison(t)

    outliers = []
    for c in bench.get("comparisons") or []:
        if c.get("percentile", 50) >= 90 or c.get("percentile", 50) <= 10:
            outliers.append(
                {
                    "metric": c["metric"],
                    "percentile": c["percentile"],
                    "rank": c["peer_rank"],
                    "value": c["value"],
                }
            )

    return {
        "ticker": t,
        "found": bool(pack),
        "sector": pack["sector"] if pack else None,
        "peer_matrix": {
            "direct": resolved.get("direct") or [],
            "global": resolved.get("global_leaders") or [],
            "historical": resolved.get("historical_leaders") or [],
        },
        "ranking_summary": ranks.get("dimensions") or {},
        "metric_ranks": ranks.get("metric_ranks") or [],
        "outliers": outliers,
        "comparisons": bench.get("comparisons") or [],
        "narrative": comment.get("narrative"),
        "trajectory_insight": comment.get("trajectory_insight"),
        "confidence": conf,
        "missing_peer_data": pack.get("missing") if pack else ["no_pack"],
        "audience": {
            "committee": "peer scorecards + ranking summary + outliers",
            "cio": "institutional comparison narrative",
            "research_writer": "peer tables / percentile / trend fields",
            "business_analyst": "business_quality + funding/moat relative ranks",
            "financial_analyst": "financial_quality + percentiles + trends",
            "valuation_analyst": "valuation dimension + premium vs peers/history",
            "risk_analyst": "asset_quality + capital relative ranks",
        },
    }
