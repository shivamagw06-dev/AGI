"""Financial / valuation / sector KPI benchmarking."""

from __future__ import annotations

from typing import Any

from peer_intelligence.historical.series import history_for
from peer_intelligence.percentile.engine import percentiles_for
from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker
from peer_intelligence.rankings.engine import rankings_for
from peer_intelligence.sector_models.kpis import sector_model
from peer_intelligence.trends.engine import trends_for


def benchmarks_for(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return {"ticker": t, "found": False}
    pct = percentiles_for(t)
    hist = history_for(t)
    ranks = rankings_for(t)
    trends = trends_for(t)
    model = sector_model(pack["sector"])

    comparisons = []
    trend_map = {x["metric"]: x for x in trends.get("trends") or []}
    hist_map = {x["metric"]: x for x in hist.get("series") or []}
    for p in pct.get("percentiles") or []:
        h = hist_map.get(p["metric"]) or {}
        tr = trend_map.get(p["metric"]) or {}
        comparisons.append(
            {
                "metric": p["metric"],
                "value": p["value"],
                "peer_rank": p["rank"],
                "peer_n": p["n"],
                "percentile": p["percentile"],
                "sector_median": p["median"],
                "vs_own_5y_avg": h.get("vs_own_5y_avg"),
                "own_5y_avg": (h.get("stats") or {}).get("5y_avg"),
                "trend": tr.get("trend"),
                "source": p.get("source"),
                "relative_statement": _relative_line(t, p, h, tr),
            }
        )

    return {
        "ticker": t,
        "found": True,
        "sector": pack["sector"],
        "sector_model": model,
        "comparisons": comparisons,
        "dimensions": ranks.get("dimensions") or {},
        "missing": pack.get("missing") or [],
    }


def _relative_line(ticker: str, p: dict[str, Any], h: dict[str, Any], tr: dict[str, Any]) -> str:
    metric = p["metric"]
    rank = p["rank"]
    n = p["n"]
    vs = h.get("vs_own_5y_avg")
    hist_bit = ""
    if vs is not None:
        hist_bit = (
            f" and is {'above' if vs > 0 else 'below' if vs < 0 else 'in line with'} "
            f"its own multi-year average"
        )
    trend_bit = f" Trend: {tr.get('trend')}." if tr.get("trend") else ""
    return (
        f"{ticker} {metric} ranks {rank} of {n} in the direct peer set "
        f"(percentile {p['percentile']}){hist_bit}.{trend_bit}"
    )
