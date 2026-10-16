"""Sector / geography allocation + drift vs benchmark."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def allocation_analysis(
    holdings: list[dict[str, Any]],
    *,
    cash_weight: float,
    benchmark: dict[str, float] | None,
    sector_limits: dict[str, float] | None,
) -> dict[str, Any]:
    sector_w: dict[str, float] = defaultdict(float)
    country_w: dict[str, float] = defaultdict(float)
    for h in holdings:
        sector_w[str(h.get("sector") or "other")] += float(h.get("weight") or 0)
        country_w[str(h.get("country") or "UNK")] += float(h.get("weight") or 0)
    sector_w["cash"] = float(cash_weight or 0)

    bench = benchmark or {}
    active = {
        s: round(sector_w.get(s, 0.0) - float(bench.get(s, 0.0)), 4)
        for s in set(list(sector_w) + list(bench))
    }
    limits = sector_limits or {}
    breaches = [
        {"sector": s, "weight": round(w, 4), "limit": limits[s]}
        for s, w in sector_w.items()
        if s in limits and w > float(limits[s]) + 1e-9
    ]
    return {
        "sector_weights": {k: round(v, 4) for k, v in sorted(sector_w.items())},
        "country_weights": {k: round(v, 4) for k, v in sorted(country_w.items())},
        "benchmark_weights": bench,
        "active_weights": active,
        "sector_limit_breaches": breaches,
        "cash_weight": round(float(cash_weight or 0), 4),
    }
