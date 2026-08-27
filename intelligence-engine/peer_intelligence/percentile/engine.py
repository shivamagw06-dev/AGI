"""Percentile engine — sector percentile for every metric."""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker

# Metrics where lower is better
LOWER_BETTER = {"GNPA", "NNPA", "Credit_Cost", "Attrition", "CAC", "Cost_of_Funds", "Deposit_Beta"}


def _latest(points: dict[str, float]) -> float | None:
    if not points:
        return None
    return list(points.values())[-1]


def percentiles_for(ticker: str, *, universe: str = "direct") -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return {"ticker": t, "found": False, "percentiles": []}

    uni = set(
        pack.get("direct_universe")
        if universe == "direct"
        else (pack.get("direct_universe") or []) + (pack.get("global_universe") or [])
    )
    # group series by metric
    by_metric: dict[str, dict[str, float]] = {}
    sources: dict[str, str] = {}
    for s in pack.get("series") or []:
        ent = s.get("entity")
        if ent not in uni:
            continue
        m = s.get("metric")
        val = _latest(s.get("points") or {})
        if m is None or val is None:
            continue
        by_metric.setdefault(m, {})[ent] = val
        sources[m] = s.get("source") or ""

    out = []
    for metric, vals in by_metric.items():
        if t not in vals:
            continue
        subject = vals[t]
        peers = list(vals.values())
        lower = metric in LOWER_BETTER
        # percentile: % of peers the subject beats
        if lower:
            beat = sum(1 for v in peers if subject < v)
        else:
            beat = sum(1 for v in peers if subject > v)
        pct = round(100.0 * beat / max(1, len(peers) - 1), 1) if len(peers) > 1 else 50.0
        # rank 1 = best
        ordered = sorted(vals.items(), key=lambda kv: kv[1], reverse=not lower)
        rank = next((i + 1 for i, (e, _) in enumerate(ordered) if e == t), None)
        out.append(
            {
                "metric": metric,
                "value": subject,
                "percentile": pct,
                "rank": rank,
                "n": len(peers),
                "universe": sorted(vals.keys()),
                "median": sorted(peers)[len(peers) // 2],
                "best": ordered[0][0] if ordered else None,
                "lower_better": lower,
                "source": sources.get(metric, ""),
            }
        )
    out.sort(key=lambda r: -r["percentile"])
    return {
        "ticker": t,
        "found": True,
        "sector": pack["sector"],
        "universe_mode": universe,
        "percentiles": out,
    }
