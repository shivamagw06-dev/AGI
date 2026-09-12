"""Constrained portfolio construction and portfolio-level risk intelligence."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence


def construct(
    candidates: Iterable[Mapping[str, Any]],
    *,
    capital: float,
    max_position_weight: float = 0.05,
    max_sector_weight: float = 0.25,
    max_adv_participation: float = 0.05,
    long_short: bool = False,
) -> dict[str, Any]:
    rows = [dict(row) for row in candidates if float(row.get("volatility") or 0.0) > 0]
    if capital <= 0:
        raise ValueError("capital_must_be_positive")
    if not rows:
        return {"positions": [], "cash_weight": 1.0, "warnings": ["no_eligible_candidates"]}
    raw = []
    for row in rows:
        score = float(row.get("score") or 0.0)
        if not long_short and score <= 0:
            continue
        strength = abs(score) / float(row["volatility"])
        raw.append((row, strength, 1.0 if score >= 0 else -1.0))
    total_strength = sum(item[1] for item in raw) or 1.0
    sector_used: dict[str, float] = defaultdict(float)
    positions = []
    for row, strength, sign in sorted(raw, key=lambda item: item[1], reverse=True):
        sector = str(row.get("sector") or "UNKNOWN")
        desired = strength / total_strength
        position_cap = min(max_position_weight, max(0.0, max_sector_weight - sector_used[sector]))
        adv = float(row.get("adv") or 0.0)
        liquidity_cap = adv * max_adv_participation / capital if adv > 0 else 0.0
        weight = min(desired, position_cap, liquidity_cap) * sign
        if abs(weight) <= 0:
            continue
        sector_used[sector] += abs(weight)
        positions.append({**row, "weight": weight, "notional": capital * weight})
    gross = sum(abs(row["weight"]) for row in positions)
    return {
        "positions": positions,
        "gross_exposure": gross,
        "net_exposure": sum(row["weight"] for row in positions),
        "cash_weight": max(0.0, 1.0 - gross) if not long_short else 0.0,
        "sector_weights": dict(sector_used),
        "warnings": [] if positions else ["constraints_removed_all_candidates"],
    }


def risk_report(
    positions: Sequence[Mapping[str, Any]],
    *,
    portfolio_returns: Sequence[float] = (),
    factor_keys: Sequence[str] = ("value", "quality", "growth", "momentum"),
) -> dict[str, Any]:
    weights = [float(row.get("weight") or 0.0) for row in positions]
    sector: dict[str, float] = defaultdict(float)
    factors: dict[str, float] = defaultdict(float)
    liquidity_days = []
    beta = 0.0
    for row, weight in zip(positions, weights):
        sector[str(row.get("sector") or "UNKNOWN")] += weight
        beta += weight * float(row.get("beta") or 0.0)
        for factor in factor_keys:
            factors[factor] += weight * float(row.get(f"{factor}_exposure") or 0.0)
        adv = float(row.get("adv") or 0.0)
        notional = abs(float(row.get("notional") or 0.0))
        if adv > 0:
            liquidity_days.append(notional / adv)
    peak = 1.0
    nav = 1.0
    drawdown = 0.0
    for value in portfolio_returns:
        nav *= 1.0 + float(value)
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1.0)
    volatility = statistics.stdev(portfolio_returns) * math.sqrt(252.0) if len(portfolio_returns) > 1 else None
    return {
        "gross_exposure": sum(abs(value) for value in weights),
        "net_exposure": sum(weights),
        "beta": beta,
        "single_stock_max": max((abs(value) for value in weights), default=0.0),
        "sector_exposure": dict(sector),
        "factor_exposure": dict(factors),
        "liquidity_days_max": max(liquidity_days, default=None),
        "annualized_volatility": volatility,
        "max_drawdown": drawdown,
    }
