"""Trend engine — improving / stable / deteriorating / accelerating…"""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker
from peer_intelligence.percentile.engine import LOWER_BETTER


def _label(vals: list[float], lower_better: bool) -> str:
    if len(vals) < 2:
        return "stable"
    recent = vals[-3:] if len(vals) >= 3 else vals
    first, last = recent[0], recent[-1]
    delta = last - first
    # acceleration: last step vs prior step
    if len(vals) >= 3:
        step1 = vals[-2] - vals[-3]
        step2 = vals[-1] - vals[-2]
    else:
        step1 = step2 = delta

    if lower_better:
        delta = -delta
        step1, step2 = -step1, -step2

    if abs(delta) < 0.05 * (abs(first) + 1e-9):
        base = "stable"
    elif delta > 0:
        base = "improving"
    else:
        base = "deteriorating"

    if base == "improving" and step2 > step1 > 0:
        return "accelerating"
    if base == "improving" and step2 < step1 and step2 > 0:
        return "decelerating"
    if base == "deteriorating" and last > first * 0.0 and vals[0] > vals[-1] and vals[-1] > vals[-2]:
        return "recovering"
    if base == "deteriorating" and abs(delta) > 0.15 * (abs(first) + 1e-9):
        return "breaking"
    return base


def trends_for(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return {"ticker": t, "found": False, "trends": []}
    out = []
    for s in pack.get("series") or []:
        if s.get("entity") != t:
            continue
        vals = list((s.get("points") or {}).values())
        metric = s.get("metric") or ""
        label = _label(vals, metric in LOWER_BETTER)
        out.append(
            {
                "metric": metric,
                "trend": label,
                "points": s.get("points") or {},
                "latest": vals[-1] if vals else None,
                "change_3pt": round(vals[-1] - vals[0], 4) if len(vals) >= 2 else None,
            }
        )
    return {"ticker": t, "found": True, "sector": pack["sector"], "trends": out}
