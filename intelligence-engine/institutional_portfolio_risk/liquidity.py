"""PRE-01 liquidity engine — ADV / exit-days proxies (deterministic)."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio_risk.models import LiquidityRisk

# Approximate INR ADV (notional) for liquid Indian large-caps — deterministic fixtures.
_ADV_INR: dict[str, float] = {
    "HDFCBANK": 8_000_000_000,
    "ICICIBANK": 7_500_000_000,
    "AXISBANK": 4_500_000_000,
    "KOTAKBANK": 3_500_000_000,
    "RELIANCE": 10_000_000_000,
    "TCS": 4_000_000_000,
    "INFY": 3_500_000_000,
    "SBIN": 6_000_000_000,
}

_DEFAULT_ADV = 1_500_000_000
_PARTICIPATION = 0.10  # 10% of ADV assumed executable per day


def _adv(ticker: str) -> float:
    return float(_ADV_INR.get(str(ticker).upper(), _DEFAULT_ADV))


def _exit_days(market_value: float, adv: float) -> float:
    capacity = adv * _PARTICIPATION
    if capacity <= 0:
        return 999.0
    return max(0.0, float(market_value) / capacity)


def _level(*, avg_exit: float, illiquid_w: float, cash_w: float, score: float) -> str:
    if avg_exit >= 10 or illiquid_w >= 0.25 or score < 35:
        return "Critical"
    if avg_exit >= 5 or illiquid_w >= 0.15 or score < 55:
        return "High"
    if avg_exit >= 2 or illiquid_w >= 0.08 or score < 70:
        return "Moderate"
    if cash_w >= 0.15 and avg_exit < 1.5:
        return "Low"
    return "Low" if score >= 70 else "Moderate"


def evaluate_liquidity(
    holdings: Sequence[HoldingRecord],
    *,
    cash_weight: float = 0.0,
) -> LiquidityRisk:
    positions: list[dict] = []
    weighted_exit = 0.0
    equity_w = 0.0
    illiquid_w = 0.0

    for h in holdings:
        w = float(h.weight or 0.0)
        mv = float(h.market_value or 0.0)
        if mv <= 0 and w > 0:
            # Infer notional from weight assuming 10M book
            mv = w * 10_000_000
        adv = _adv(h.ticker)
        days = _exit_days(mv, adv)
        illiquid = days >= 5.0
        if illiquid:
            illiquid_w += w
        weighted_exit += days * w
        equity_w += w
        positions.append(
            {
                "ticker": h.ticker,
                "weight": round(w, 6),
                "market_value": round(mv, 2),
                "adv_inr": adv,
                "exit_days": round(days, 3),
                "illiquid": illiquid,
            }
        )

    avg_exit = (weighted_exit / equity_w) if equity_w > 0 else 0.0
    # Score: higher = more liquid
    score = 100.0
    score -= min(50.0, avg_exit * 8.0)
    score -= min(30.0, illiquid_w * 100.0)
    score += min(15.0, float(cash_weight) * 50.0)
    score = max(0.0, min(100.0, score))

    level = _level(
        avg_exit=avg_exit,
        illiquid_w=illiquid_w,
        cash_w=float(cash_weight),
        score=score,
    )
    return LiquidityRisk(
        level=level,
        portfolio_liquidity_score=round(score, 2),
        average_exit_days=round(avg_exit, 3),
        illiquid_weight=round(illiquid_w, 6),
        cash_weight=round(float(cash_weight), 6),
        positions=tuple(positions),
    )
