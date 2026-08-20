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
# A monthly move beyond this is treated as a price error rather than a return.
# The universe benchmark is an unranked average, so a single symbol whose split
# went unadjusted - 104 corporate actions still contradict their stated ratio -
# drags the whole month. It reported 480% annualised volatility and a -1,817%
# drawdown, both impossible. The ranked books were unaffected because a bad
# price has to also rank top or bottom to enter them.
MAX_PLAUSIBLE_MONTHLY_RETURN = 1.0


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


def rank_ic(scores: dict[str, float], forward: dict[str, float]) -> Optional[float]:
    """Spearman rank correlation between signal and next-month return.

    The cleanest read on whether a signal carries information. A long-only
    portfolio is dominated by market direction - it can lose money in a falling
    market while ranking names perfectly - so the level of its return says
    little about the signal. The rank correlation says it directly.
    """
    pairs = [(scores[s], forward[s]) for s in scores if s in forward]
    if len(pairs) < 10:
        return None

    def _ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out

    xs = _ranks([p[0] for p in pairs])
    ys = _ranks([p[1] for p in pairs])
    n = len(pairs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(xs, ys))
    var_x = sum((a - mean_x) ** 2 for a in xs)
    var_y = sum((b - mean_y) ** 2 for b in ys)
    if var_x <= 0 or var_y <= 0:
        return None
    return cov / math.sqrt(var_x * var_y)


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
        # Forward return for every name that carried a signal, not just the
        # ones bought. This is what makes the benchmark and the IC possible.
        forward: dict[str, float] = {}
        discarded = 0
        for symbol in scores[month]:
            start = (prices.get(symbol) or {}).get(month)
            end = (prices.get(symbol) or {}).get(nxt)
            if not (start and end and start > 0):
                continue
            move = end / start - 1.0
            if abs(move) > MAX_PLAUSIBLE_MONTHLY_RETURN:
                discarded += 1
                continue
            forward[symbol] = move

        ranked = [s for s, _ in sorted(scores[month].items(), key=lambda kv: -kv[1])
                  if s in forward]
        if len(ranked) < 20:
            periods.append({"month": month, "n": len(ranked), "net": None,
                            "reason": "too_few_priced_candidates"})
            continue

        picks = ranked[:holdings]
        shorts = ranked[-holdings:]
        gross = sum(forward[s] for s in picks) / len(picks)
        # The universe of covered names, equally weighted: the benchmark this
        # portfolio was actually selected from. Beating it is the only claim a
        # long-only strategy can make; its raw return is mostly market
        # direction, which is why -18% out of sample said little on its own.
        universe = sum(forward.values()) / len(forward)
        spread = gross - (sum(forward[s] for s in shorts) / len(shorts))

        new_holdings = set(picks)
        turnover = len(new_holdings - held) / max(1, len(new_holdings))
        cost = turnover * (cost_bps / 10_000.0) * 2
        periods.append({
            "month": month, "n": len(picks), "gross": round(gross, 6),
            "net": round(gross - cost, 6), "turnover": round(turnover, 4),
            "universe": round(universe, 6),
            "excess": round(gross - cost - universe, 6),
            "long_short": round(spread - cost, 6),
            "ic": rank_ic(scores[month], forward),
            "breadth": len(forward),
            "implausible_returns_discarded": discarded,
        })
        held = new_holdings

    def series(key: str, window: Optional[str] = None) -> list[float]:
        return [p[key] for p in periods
                if p.get(key) is not None
                and (window is None
                     or (window == "in" and p["month"] < oos_start)
                     or (window == "out" and p["month"] >= oos_start))]

    net = series("net")
    ics = [p["ic"] for p in periods if p.get("ic") is not None]
    ics_out = [p["ic"] for p in periods if p.get("ic") is not None and p["month"] >= oos_start]

    return {
        "ok": bool(net),
        "strategy": "estimate_revision_long_only",
        "signal": f"consensus EPS revision over {lookback_months} months, same target fiscal year",
        "settings": {"lookback_months": lookback_months, "holdings": holdings,
                     "cost_bps": cost_bps, "oos_start": oos_start,
                     "rebalance": "monthly", "weighting": "equal"},
        "coverage": {
            "implausible_returns_discarded": sum(
                p.get("implausible_returns_discarded") or 0 for p in periods),
            "months_evaluated": len(periods),
            "months_with_a_portfolio": len(net),
            "symbols_with_a_signal": len({s for month in scores.values() for s in month}),
            "symbols_with_prices": len(prices),
        },
        "net": _metrics(net),
        "in_sample": _metrics(series("net", "in")),
        "out_of_sample": _metrics(series("net", "out")),
        # Return relative to the covered universe, which is what a long-only
        # ranked strategy can actually claim.
        "excess_over_universe": _metrics(series("excess")),
        "excess_out_of_sample": _metrics(series("excess", "out")),
        "universe_benchmark": _metrics(series("universe")),
        "long_short": _metrics(series("long_short")),
        "long_short_out_of_sample": _metrics(series("long_short", "out")),
        "information_coefficient": {
            "mean": round(sum(ics) / len(ics), 4) if ics else None,
            "mean_out_of_sample": round(sum(ics_out) / len(ics_out), 4) if ics_out else None,
            "months_positive_pct": round(sum(1 for i in ics if i > 0) / len(ics) * 100, 1) if ics else None,
            "note": "Spearman rank correlation between the revision and the next "
                    "month's return, across every covered name. A mean near zero "
                    "means the ranking carries no information, whatever the "
                    "portfolio returned.",
        },
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
