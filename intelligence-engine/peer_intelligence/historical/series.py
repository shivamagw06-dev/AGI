"""Historical context engine — never standalone observations."""

from __future__ import annotations

from statistics import median
from typing import Any

from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker


def _stats(points: dict[str, float]) -> dict[str, Any]:
    vals = list(points.values())
    if not vals:
        return {}
    # order by period key roughly
    items = list(points.items())
    latest_period, latest = items[-1]
    return {
        "latest_period": latest_period,
        "latest": latest,
        "min": min(vals),
        "max": max(vals),
        "average": round(sum(vals) / len(vals), 4),
        "median": round(float(median(vals)), 4),
        "n": len(vals),
        "1y": vals[-1] if len(vals) >= 1 else None,
        "3y_avg": round(sum(vals[-3:]) / min(3, len(vals)), 4) if vals else None,
        "5y_avg": round(sum(vals[-5:]) / min(5, len(vals)), 4) if vals else None,
        "10y_avg": round(sum(vals) / len(vals), 4),
    }


def history_for(ticker: str, metric: str | None = None) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return {"ticker": t, "found": False, "series": []}
    rows = []
    for s in pack.get("series") or []:
        if s.get("entity") != t:
            continue
        if metric and s.get("metric") != metric:
            continue
        pts = s.get("points") or {}
        st = _stats(pts)
        vs_own = None
        if st and st.get("latest") is not None and st.get("5y_avg") is not None:
            vs_own = round(st["latest"] - st["5y_avg"], 4)
        rows.append(
            {
                **s,
                "stats": st,
                "vs_own_5y_avg": vs_own,
                "context": _own_context(s.get("metric"), st, vs_own),
            }
        )
    return {"ticker": t, "found": True, "sector": pack["sector"], "series": rows}


def _own_context(metric: str | None, st: dict[str, Any], vs_own: float | None) -> str:
    if not st or vs_own is None:
        return "Insufficient history"
    direction = "above" if vs_own > 0 else "below" if vs_own < 0 else "in line with"
    return (
        f"{metric} latest {st['latest']} is {direction} its own multi-year average "
        f"({st['5y_avg']}; range {st['min']}–{st['max']})."
    )
