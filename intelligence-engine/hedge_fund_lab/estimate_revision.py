"""Estimate-revision strategy: rank on how analysts changed their minds.

The five intraday engines compete on speed against co-located participants and
cannot win that race. This one competes on data assembly instead, which is the
edge this warehouse actually has: 258,465 point-in-time consensus vintages,
monthly from 2020, on a market where only 910 of 2,714 listed companies carry
any sell-side coverage at all.

The signal is the change in the consensus EPS estimate for a *fixed* fiscal
year, measured across months:

    revision(t) = estimate(FY, t) / estimate(FY, t - k) - 1

Holding the target period fixed is the whole discipline. Indian fiscal years
roll in April, so an unguarded comparison in month 13 divides next year's
estimate by this year's and reports a fictitious revision of whatever the
growth rate happens to be. Months where the same FY has no earlier vintage
produce no signal rather than a wrong one.

Point-in-time is free here in a way it is not elsewhere: a vintage dated
2021-06-30 is what was believed on 2021-06-30, so ranking on it and measuring
the following month's return involves no look-ahead. That is exactly what
`financials_annual` cannot support, since it carries fiscal year ends and no
publication dates.

What this still cannot do is survive survivorship. The universe is companies
listed today, and a ranked long portfolio is precisely where that bias does its
worst work: the names that would have been dropped are the ones that failed.
Every result carries the warning, and no figure here is an alpha claim.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date
from typing import Any, Iterable, Optional

from .price_adjustment import _as_date, is_trading_day

MONTHS_PER_YEAR = 12
DEFAULT_LOOKBACK_MONTHS = 3
DEFAULT_HOLDINGS = 25
# Round trip, matching the price backtests: brokerage, STT, impact and spread.
DEFAULT_COST_BPS = 25.0
# Monthly rebalance, so 2024 onward stays frozen out of sample.
DEFAULT_OOS_START = "2024-01"
# A tiny estimate makes the denominator explode; 1 rupee of EPS is the floor.
MIN_ABS_ESTIMATE = 1.0


def _month(value: Any) -> Optional[str]:
    parsed = _as_date(str(value)[:10]) if value else None
    return f"{parsed.year:04d}-{parsed.month:02d}" if parsed else None


def _shift(month: str, back: int) -> str:
    year, mon = int(month[:4]), int(month[5:7])
    total = year * 12 + (mon - 1) - back
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def revision_scores(
    vintage_rows: Iterable[dict[str, Any]],
    lookback_months: int = DEFAULT_LOOKBACK_MONTHS,
) -> dict[str, dict[str, float]]:
    """{month: {symbol: revision}} from point-in-time consensus vintages.

    Only forward estimates count, and only comparisons within one target fiscal
    year. A month with no earlier vintage for that same year yields nothing.
    """
    # (symbol, target_period) -> {month: estimate}
    series: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in vintage_rows or []:
        if str(row.get("metric") or "") != "eps_estimate":
            continue
        if str(row.get("is_forward_estimate") or "").lower() != "true":
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        target = str(row.get("target_period") or "").strip()
        month = _month(row.get("consensus_date"))
        try:
            estimate = float(row.get("mean_estimate"))
        except (TypeError, ValueError):
            continue
        if not symbol or not target or not month or estimate == 0:
            continue
        series[(symbol, target)][month] = estimate

    out: dict[str, dict[str, float]] = defaultdict(dict)
    for (symbol, _target), by_month in series.items():
        for month, current in by_month.items():
            prior = by_month.get(_shift(month, lookback_months))
            if prior is None or abs(prior) < MIN_ABS_ESTIMATE:
                continue
            # A sign flip is a change of a different kind - loss to profit is
            # not a percentage revision - so it is excluded rather than scaled.
            if (prior > 0) != (current > 0):
                continue
            revision = current / prior - 1.0
            # One symbol can hold two target years in the same month around the
            # April roll. Keep the larger absolute revision: it is the more
            # informative of the two and the choice is deterministic.
            existing = out[month].get(symbol)
            if existing is None or abs(revision) > abs(existing):
                out[month][symbol] = revision
    return dict(out)


def monthly_prices(price_rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """{symbol: {YYYY-MM: last adjusted close}} from daily bars.

    Weekend rows are dropped: they carry a differently scaled series and would
    otherwise decide the month-end price.
    """
    latest: dict[str, dict[str, tuple[date, float]]] = defaultdict(dict)
    for row in price_rows or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        when = _as_date(str(row.get("date") or "")[:10])
        try:
            close = float(row.get("close"))
        except (TypeError, ValueError):
            continue
        if not symbol or when is None or close <= 0 or not is_trading_day(when):
            continue
        month = f"{when.year:04d}-{when.month:02d}"
        seen = latest[symbol].get(month)
        if seen is None or when > seen[0]:
            latest[symbol][month] = (when, close)
    return {symbol: {m: price for m, (_, price) in months.items()}
            for symbol, months in latest.items()}


def _metrics(returns: list[float]) -> dict[str, Any]:
    """Monthly returns annualised by 12. Never by 252 - these are not days."""
    if len(returns) < 2:
        return {"months": len(returns), "insufficient_data": True}
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0)
    years = len(returns) / MONTHS_PER_YEAR
    annualised = equity ** (1 / years) - 1 if years > 0 and equity > 0 else None
    volatility = statistics.stdev(returns) * math.sqrt(MONTHS_PER_YEAR)
    return {
        "months": len(returns),
        "cumulative_return_pct": round((equity - 1.0) * 100, 3),
        "annualised_return_pct": round(annualised * 100, 3) if annualised is not None else None,
        "annualised_volatility_pct": round(volatility * 100, 3),
        # Excess over cash is not modelled, so this is return over volatility
        # rather than a Sharpe ratio, and is named accordingly.
        "return_over_vol": round(annualised / volatility, 3)
        if annualised is not None and volatility > 1e-9 else None,
        "max_drawdown_pct": round(max_drawdown * 100, 3),
        "win_rate_pct": round(sum(1 for r in returns if r > 0) / len(returns) * 100, 2),
    }


def backtest(
    *,
    vintage_rows: Iterable[dict[str, Any]],
    price_rows: Iterable[dict[str, Any]],
    lookback_months: int = DEFAULT_LOOKBACK_MONTHS,
    holdings: int = DEFAULT_HOLDINGS,
    cost_bps: float = DEFAULT_COST_BPS,
    oos_start: str = DEFAULT_OOS_START,
) -> dict[str, Any]:
    """Monthly walk-forward: rank on revision, hold one month, pay costs."""
    scores = revision_scores(vintage_rows, lookback_months=lookback_months)
    prices = monthly_prices(price_rows)
    if not scores:
        return {"ok": False, "error": "no_revision_signal"}
    if not prices:
        return {"ok": False, "error": "no_price_history"}

    months = sorted(scores)
    periods: list[dict[str, Any]] = []
    held: set[str] = set()

    for month in months:
        nxt = _shift(month, -1)
        ranked = sorted(scores[month].items(), key=lambda kv: -kv[1])
        picks: list[tuple[str, float]] = []
        for symbol, _score in ranked:
            start = (prices.get(symbol) or {}).get(month)
            end = (prices.get(symbol) or {}).get(nxt)
            if start and end and start > 0:
                picks.append((symbol, end / start - 1.0))
            if len(picks) >= holdings:
                break
        if len(picks) < 5:
            periods.append({"month": month, "n": len(picks), "net": None,
                            "reason": "too_few_priced_candidates"})
            continue
        gross = sum(r for _, r in picks) / len(picks)
        new = {s for s, _ in picks}
        turnover = len(new - held) / max(1, len(new))
        cost = turnover * (cost_bps / 10_000.0) * 2
        periods.append({"month": month, "n": len(picks), "gross": round(gross, 6),
                        "net": round(gross - cost, 6), "turnover": round(turnover, 4)})
        held = new

    net = [p["net"] for p in periods if p.get("net") is not None]
    in_sample = [p["net"] for p in periods if p.get("net") is not None and p["month"] < oos_start]
    out_sample = [p["net"] for p in periods if p.get("net") is not None and p["month"] >= oos_start]

    return {
        "ok": bool(net),
        "strategy": "estimate_revision_long_only",
        "signal": f"consensus EPS revision over {lookback_months} months, same target fiscal year",
        "settings": {"lookback_months": lookback_months, "holdings": holdings,
                     "cost_bps": cost_bps, "oos_start": oos_start,
                     "rebalance": "monthly", "weighting": "equal"},
        "coverage": {
            "months_evaluated": len(periods),
            "months_with_a_portfolio": len(net),
            "symbols_with_a_signal": len({s for month in scores.values() for s in month}),
            "symbols_with_prices": len(prices),
        },
        "net": _metrics(net),
        "in_sample": _metrics(in_sample),
        "out_of_sample": _metrics(out_sample),
        "periods": periods,
        "limitations": [
            "SURVIVORSHIP: the universe is companies listed today. A ranked long "
            "portfolio is where that bias does its worst work, because the names "
            "that would have been dropped are the ones that failed. These figures "
            "are flattered by an unknown and probably large amount.",
            "Only companies with sell-side coverage can carry a revision signal - "
            "roughly 910 of 2,714 - so this strategy addresses a third of the "
            "listed universe by construction.",
            "Equal weight. No volatility targeting or liquidity cap, because "
            "historical ATR and ADV are not available per past month.",
            "Price return only; dividends are not reinvested.",
            "Costs are a flat round trip. Impact is not modelled, so results do "
            "not hold at size in thin names.",
        ],
        "verdict": "Research evidence only. Survivorship alone disqualifies these "
                   "figures from an alpha claim, however they read.",
    }
