"""Quality among companies nobody covers.

Estimate revision failed for a structural reason worth remembering: its
information sat in small and mid caps, and the only names that can be shorted
in India are the 214 with single-stock futures - the largest and most
arbitraged in the market. The edge was real and unreachable.

This strategy is built to avoid both traps. It is long-only, so shortability
never binds, and it deliberately targets the companies with no sell-side
coverage at all: 2,714 listed names, 910 with an analyst, leaving roughly 1,800
where the only reason a mispricing would persist is that nobody has looked. The
moat is coverage, not cleverness.

The signal is a rank composite over four fundamentals from the ten-year Capital
IQ panel:

    roe          higher is better - returns on owner capital
    roa          higher is better - returns unlevered by balance sheet
    ebitda_margin higher is better - operating quality
    debt_equity  lower is better  - survivability

Each is ranked within the company's own sector, because a 12% ROE means
different things for a bank and a software firm, and the panel is already
sector-aware. Missing metrics reduce the number of components rather than
scoring zero: an absent reading is not a bad reading.

Point-in-time is handled by a filing lag rather than assumed away. The panel
carries fiscal year ends and no publication dates, so FY2025 data stamped
2025-03-31 was not public on that date - full-year audited results follow it by
months. Every observation is therefore withheld until `LAG_MONTHS` after its
fiscal year end. That is a conservative assumption, not evidence, and it is
declared on every result.

Survivorship is unfixed and matters more here than anywhere else: a quality
screen over survivors selects companies that did not go bankrupt, which is
close to selecting on the outcome.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Optional

from .estimate_revision import (
    MAX_PLAUSIBLE_MONTHLY_RETURN,
    _metrics,
    _shift,
    monthly_prices,
    rank_ic,
)

# Higher is better unless the metric is listed as inverted.
QUALITY_METRICS = ("roe", "roa", "ebitda_margin", "debt_equity")
INVERTED = {"debt_equity"}
# Months after fiscal year end before a figure is treated as public. Indian
# full-year audited results are filed within 60 days, but the panel gives no
# actual filing date, so this is deliberately slower than the legal minimum.
LAG_MONTHS = 6
MIN_COMPONENTS = 2
DEFAULT_HOLDINGS = 30
DEFAULT_COST_BPS = 25.0
DEFAULT_OOS_START = "2024-01"


def _fiscal_year_end_month(fiscal_year: str) -> Optional[str]:
    """FY2025 ends March 2025 on the Indian calendar."""
    text = str(fiscal_year or "").strip().upper()
    if not text.startswith("FY") or not text[2:].isdigit():
        return None
    year = int(text[2:])
    if year < 1990 or year > 2100:
        return None
    return f"{year:04d}-03"


def available_from(fiscal_year: str, lag_months: int = LAG_MONTHS) -> Optional[str]:
    """First month the figure may be used without look-ahead."""
    end = _fiscal_year_end_month(fiscal_year)
    return _shift(end, -lag_months) if end else None


def quality_scores(
    ratio_rows: Iterable[dict[str, Any]],
    *,
    covered: Optional[set[str]] = None,
    lag_months: int = LAG_MONTHS,
) -> dict[str, dict[str, float]]:
    """{month: {symbol: composite}} ranked within sector, point-in-time.

    `covered` is the set of symbols with analyst coverage. When supplied they
    are excluded, which is the whole point: the strategy is a bet on the names
    nobody models.
    """
    # month -> sector -> metric -> [(symbol, value)]
    panel: dict[str, dict[str, dict[str, list[tuple[str, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list)))
    # A company's newest *available* figure for each metric, by month.
    latest: dict[tuple[str, str, str], tuple[str, float, str]] = {}

    for row in ratio_rows or []:
        if str(row.get("median_eligibility") or "").upper() != "ELIGIBLE":
            continue
        metric = str(row.get("metric") or "").lower()
        symbol = str(row.get("symbol") or "").strip().upper()
        sector = str(row.get("sector") or "").strip() or "UNCLASSIFIED"
        fiscal_year = str(row.get("fiscal_year") or "")
        if metric not in QUALITY_METRICS or not symbol:
            continue
        if covered and symbol in covered:
            continue
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        usable_from = available_from(fiscal_year, lag_months)
        if not usable_from:
            continue
        key = (symbol, metric, usable_from)
        prior = latest.get(key)
        if prior is None or fiscal_year > prior[2]:
            latest[key] = (sector, value, fiscal_year)

    # Carry each observation forward from the month it became available until
    # a newer fiscal year supersedes it. Without this a company contributes
    # only in the single month its results land.
    by_symbol_metric: dict[tuple[str, str], list[tuple[str, str, float]]] = defaultdict(list)
    for (symbol, metric, month), (sector, value, _fy) in latest.items():
        by_symbol_metric[(symbol, metric)].append((month, sector, value))

    months = sorted({m for (_s, _m, m) in
                     ((s, mt, mo) for (s, mt, mo) in latest.keys())})
    if not months:
        return {}
    horizon = _shift(months[-1], -24)
    calendar = []
    cursor = months[0]
    while cursor <= horizon:
        calendar.append(cursor)
        cursor = _shift(cursor, -1)

    for (symbol, metric), entries in by_symbol_metric.items():
        entries.sort()
        for month in calendar:
            current = None
            for start, sector, value in entries:
                if start <= month:
                    current = (sector, value)
                else:
                    break
            if current:
                panel[month][current[0]][metric].append((symbol, current[1]))

    out: dict[str, dict[str, float]] = {}
    for month, sectors in panel.items():
        totals: dict[str, list[float]] = defaultdict(list)
        for _sector, metrics in sectors.items():
            for metric, pairs in metrics.items():
                if len(pairs) < 5:
                    continue  # too thin a peer group to rank against
                ordered = sorted(pairs, key=lambda kv: kv[1], reverse=metric not in INVERTED)
                n = len(ordered)
                for index, (symbol, _value) in enumerate(ordered):
                    totals[symbol].append(1.0 - index / max(1, n - 1))
        scored = {s: sum(v) / len(v) for s, v in totals.items() if len(v) >= MIN_COMPONENTS}
        if scored:
            out[month] = scored
    return out


def backtest(
    *,
    ratio_rows: Iterable[dict[str, Any]],
    price_rows: Iterable[dict[str, Any]],
    covered: Optional[set[str]] = None,
    holdings: int = DEFAULT_HOLDINGS,
    cost_bps: float = DEFAULT_COST_BPS,
    lag_months: int = LAG_MONTHS,
    oos_start: str = DEFAULT_OOS_START,
) -> dict[str, Any]:
    """Monthly walk-forward over the uncovered universe. Long only."""
    scores = quality_scores(ratio_rows, covered=covered, lag_months=lag_months)
    prices = monthly_prices(price_rows)
    if not scores:
        return {"ok": False, "error": "no_quality_signal"}
    if not prices:
        return {"ok": False, "error": "no_price_history"}

    periods: list[dict[str, Any]] = []
    held: set[str] = set()
    for month in sorted(scores):
        nxt = _shift(month, -1)
        forward: dict[str, float] = {}
        for symbol in scores[month]:
            start = (prices.get(symbol) or {}).get(month)
            end = (prices.get(symbol) or {}).get(nxt)
            if start and end and start > 0:
                move = end / start - 1.0
                if abs(move) <= MAX_PLAUSIBLE_MONTHLY_RETURN:
                    forward[symbol] = move
        ranked = [s for s, _ in sorted(scores[month].items(), key=lambda kv: -kv[1])
                  if s in forward]
        if len(ranked) < 20:
            periods.append({"month": month, "n": len(ranked), "net": None,
                            "reason": "too_few_priced_candidates"})
            continue
        picks = ranked[:holdings]
        gross = sum(forward[s] for s in picks) / len(picks)
        universe = sum(forward.values()) / len(forward)
        new = set(picks)
        turnover = len(new - held) / max(1, len(new))
        cost = turnover * (cost_bps / 10_000.0) * 2
        periods.append({
            "month": month, "n": len(picks), "gross": round(gross, 6),
            "net": round(gross - cost, 6), "universe": round(universe, 6),
            "excess": round(gross - cost - universe, 6),
            "turnover": round(turnover, 4), "breadth": len(forward),
            "ic": rank_ic(scores[month], forward),
        })
        held = new

    def series(key: str, window: Optional[str] = None) -> list[float]:
        return [p[key] for p in periods
                if p.get(key) is not None
                and (window is None
                     or (window == "in" and p["month"] < oos_start)
                     or (window == "out" and p["month"] >= oos_start))]

    ics = [p["ic"] for p in periods if p.get("ic") is not None]
    ics_out = [p["ic"] for p in periods if p.get("ic") is not None and p["month"] >= oos_start]

    return {
        "ok": bool(series("net")),
        "strategy": "neglected_firm_quality_long_only",
        "signal": "sector-ranked composite of roe, roa, ebitda_margin and debt_equity",
        "settings": {"holdings": holdings, "cost_bps": cost_bps, "lag_months": lag_months,
                     "oos_start": oos_start, "rebalance": "monthly", "weighting": "equal",
                     "universe": "companies without analyst coverage"},
        "coverage": {
            "months_evaluated": len(periods),
            "months_with_a_portfolio": len(series("net")),
            "symbols_scored": len({s for m in scores.values() for s in m}),
            "excluded_as_covered": len(covered or ()),
        },
        "net": _metrics(series("net")),
        "in_sample": _metrics(series("net", "in")),
        "out_of_sample": _metrics(series("net", "out")),
        "excess_over_universe": _metrics(series("excess")),
        "excess_out_of_sample": _metrics(series("excess", "out")),
        "universe_benchmark": _metrics(series("universe")),
        "information_coefficient": {
            "mean": round(sum(ics) / len(ics), 4) if ics else None,
            "mean_out_of_sample": round(sum(ics_out) / len(ics_out), 4) if ics_out else None,
            "months_positive_pct": round(sum(1 for i in ics if i > 0) / len(ics) * 100, 1) if ics else None,
        },
        "limitations": [
            "SURVIVORSHIP: worse here than anywhere else. A quality screen over "
            "companies that still exist selects firms that did not go bankrupt, "
            "which is close to selecting on the outcome. Uncovered small caps are "
            "exactly the population that delists.",
            f"POINT-IN-TIME IS ASSUMED, NOT MEASURED. The panel carries fiscal year "
            f"ends and no filing dates, so every figure is withheld for "
            f"{lag_months} months after year end. That lag is a guess.",
            "Equal weight, no liquidity screen. Uncovered small caps are where "
            "impact costs are largest, so a flat cost assumption flatters this "
            "more than it would a large-cap strategy.",
            "Price return only; dividends are not reinvested.",
        ],
        "verdict": "Research evidence only. No figure here is an alpha claim.",
    }
