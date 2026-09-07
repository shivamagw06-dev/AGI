"""E10-005 Portfolio validation — weights, caps, cash, determinism helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.engines.e10.construction.select import Candidate
from app.engines.e10.mapping import NAME_CAP, SECTOR_CAP


def validate_portfolio(
    weights: dict[str, float],
    cash: float,
    candidates: list[Candidate],
    *,
    name_cap: float = NAME_CAP,
    sector_cap: float = SECTOR_CAP,
    tol: float = 1e-6,
) -> dict[str, Any]:
    equity = sum(weights.values())
    total = equity + cash
    sector_of = {c.symbol: (c.sector_id or "__UNKNOWN__") for c in candidates}
    by_sector: dict[str, float] = defaultdict(float)
    for sym, w in weights.items():
        by_sector[sector_of.get(sym, "__UNKNOWN__")] += w

    name_breaches = [s for s, w in weights.items() if w > name_cap + tol]
    sector_breaches = [sec for sec, w in by_sector.items() if w > sector_cap + tol]
    negative = [s for s, w in weights.items() if w < -tol]
    sum_ok = abs(total - 1.0) <= 1e-4
    cash_ok = cash >= -tol
    caps_ok = not name_breaches and not sector_breaches and not negative

    return {
        "ok": bool(sum_ok and cash_ok and caps_ok),
        "weights_sum": round(total, 8),
        "equity_sum": round(equity, 8),
        "cash": round(cash, 8),
        "sum_to_one": sum_ok,
        "cash_non_negative": cash_ok,
        "name_cap_ok": not name_breaches,
        "sector_cap_ok": not sector_breaches,
        "long_only_ok": not negative,
        "name_breaches": name_breaches,
        "sector_breaches": sector_breaches,
        "tolerance": tol,
    }
