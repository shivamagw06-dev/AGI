"""Corporate-action adjusted prices, corroborated against the price series.

Three defects in the warehouse make raw `close` unusable for return
measurement, all three verified against production on 2026-08-19:

1. `adjusted_close` is not adjusted. Where it is populated it equals `close`
   exactly, and the backtest receipt confirms 0 of 114 structural actions are
   reflected in it. Preferring it over `close` buys nothing.

2. `daily_market_history` contains non-trading days. Roughly 18% of rows fall
   on a Saturday or Sunday, when NSE is closed, and they carry a differently
   scaled series: MWL's Sunday prints sat at one tenth of the surrounding
   weekday prints for months before its split. Left in, every weekend injects
   a -90% day followed by a +900% day.

3. The stated split ratios are inconsistent. Measuring the price gap at 45
   structural actions:

       5:2  -> price fell 2.50x   (a/b)
       10:1 -> price fell 10.24x  (a/b)
       2:10 -> price fell 5.05x   (b/a, the other way round)
       4:3  -> price fell 1.25x   (neither reading)
       3:1  -> price fell 16.4x   (neither, and not close)

   Nineteen of forty-five matched a/b, two matched b/a, three showed no gap at
   all, and the rest matched nothing. TRENT records the same event twice, as a
   1:2 bonus and a 3:2 split, so applying both would adjust by 0.44 instead of
   0.67.

So the ratio string is a hypothesis, not an input. The observed gap in the
price series is the measurement, and an adjustment is applied only where the
two corroborate. Where they do not, the symbol is quarantined rather than
guessed at - a wrong adjustment silently rescales the entire prior history,
which is worse than no adjustment because nothing downstream can detect it.

Bonus ratios do check out: m:n gives m new shares per n held, so n shares
become n+m and prior prices scale by n/(n+m). LICI's 1:1 halved the price and
TRENT's 1:2 moved it by two thirds, both as predicted.
"""

from __future__ import annotations

import re
import statistics
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

_RATIO = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[:\-/]\s*(\d+(?:\.\d+)?)\s*$")

# How far the observed gap may sit from the stated ratio and still count as
# corroboration. Real prices move on the ex-date for ordinary reasons, so this
# cannot be tight; 6% is wide enough for a day's drift and far narrower than
# the gap between the competing a/b and b/a readings.
TOLERANCE = 0.06
# How close the observed gap must sit to 1.0 to conclude the vendor already
# restated the series. Deliberately tighter than TOLERANCE: an 11:10 split has
# a factor of 0.909 and must not be swallowed as "no gap".
NO_GAP_TOLERANCE = 0.04
# The gap is measured over calendar days, not a bar count. Early history in
# daily_market_history is monthly, so "five bars either side" spans five months
# there and ordinary price drift swamps the split. A calendar window keeps the
# comparison local on dense history and simply declines to measure on sparse
# history, which is reported as no evidence rather than a false contradiction.
GAP_WINDOW_DAYS = 10


def is_trading_day(value: date) -> bool:
    """NSE trades Monday to Friday. Weekend rows are corrupt, not sparse."""
    return value.weekday() < 5


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip()[:10], fmt).date()
            except ValueError:
                continue
    return None


def _ratio(value: Any) -> Optional[tuple[float, float]]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-", "0"}:
        return None
    m = _RATIO.match(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (a, b) if a > 0 and b > 0 else None
    try:
        n = float(text)
    except ValueError:
        return None
    return (n, 1.0) if n > 0 else None


def split_factor(value: Any) -> Optional[float]:
    """`a:b` multiplies the share count by a/b, so prior prices scale by b/a.

    Measured, not assumed: ZFCVINDIA's 6:1 took the price from 16,086 to 2,660
    and MWL's 10:1 took it from 370.25 to 36.65.
    """
    parsed = _ratio(value)
    if not parsed:
        return None
    a, b = parsed
    return b / a if a else None


def split_factor_inverted(value: Any) -> Optional[float]:
    """The competing `b/a` reading, kept so reconciliation can test both.

    A minority of rows - every `2:10` seen so far - are written the other way
    round, and only the price series can say which is meant.
    """
    parsed = _ratio(value)
    if not parsed:
        return None
    a, b = parsed
    return a / b if b else None


def bonus_factor(value: Any) -> Optional[float]:
    """`m:n` gives m new shares per n held, so n shares become n+m."""
    parsed = _ratio(value)
    if not parsed:
        return None
    m, n = parsed
    total = n + m
    return n / total if total else None


def candidate_factors(action: dict[str, Any]) -> tuple[list[float], Optional[str]]:
    """Every reading of one action worth testing against the price series."""
    kind = str(action.get("action_type") or "").strip().lower()
    if kind == "split" or action.get("split"):
        raw = action.get("split") or action.get("ratio")
        out = [f for f in (split_factor(raw), split_factor_inverted(raw))
               if f and f > 0 and f != 1.0]
        return (out, None) if out else ([], "unparseable_split")
    if kind == "bonus" or action.get("bonus"):
        f = bonus_factor(action.get("bonus") or action.get("ratio"))
        return ([f], None) if f else ([], "unparseable_bonus")
    if kind == "rights" or action.get("rights"):
        return [], "rights_not_adjusted"
    if kind == "dividend" or action.get("dividend"):
        return [], "dividend_price_return_only"
    return [], "unhandled_action_type"


def observed_factor(
    prices: list[tuple[date, float]],
    ex_date: date,
    window_days: int = GAP_WINDOW_DAYS,
) -> Optional[float]:
    """Price gap across the ex-date, as a factor applied to prior prices.

    Returns median(post) / median(pre): the number a pre-event price must be
    multiplied by to sit on the post-event share base. Only bars within
    `window_days` of the ex-date count, so a split is compared against its own
    neighbourhood rather than against a price five months away.
    """
    lower = ex_date - timedelta(days=window_days)
    upper = ex_date + timedelta(days=window_days)
    pre = [p for d, p in prices
           if p > 0 and is_trading_day(d) and lower <= d < ex_date]
    post = [p for d, p in prices
            if p > 0 and is_trading_day(d) and ex_date <= d <= upper]
    if not pre or not post:
        return None
    before = statistics.median(pre)
    return statistics.median(post) / before if before > 0 else None


def reconcile(
    candidates: list[float],
    observed: Optional[float],
    tolerance: float = TOLERANCE,
    no_gap_tolerance: float = NO_GAP_TOLERANCE,
) -> tuple[Optional[float], str]:
    """Decide what a price series says about one stated corporate action.

    Four outcomes, and the third is the one this originally got wrong:

    * corroborated - the gap matches the stated ratio; apply it.
    * series_already_adjusted - there is no gap at all. The vendor has already
      restated the history, so no factor is needed and applying one would
      double-adjust. This is a healthy state, not a failure.
    * stated_ratio_contradicted_by_prices - there is a gap, but it matches
      neither reading of the ratio. Quarantine rather than guess.
    * no_price_evidence / no_stated_ratio - nothing to compare.

    The Upstox backfill made this distinction load-bearing. Its candles arrive
    pre-adjusted, so a real 4:1 split leaves no break in the series; the old
    logic saw "no gap where a gap was stated" and called it a contradiction.
    That inverted the receipt overnight - 7 corroborated and 2 contradicted
    became 1 and 234 - and reported the cleanest price history the warehouse
    has ever held as its most suspect.

    Candidates are tested before the no-gap check on purpose. An 11:10 split
    has a factor of 0.909, close enough to 1.0 that testing "no gap" first
    would swallow it.
    """
    if observed is None:
        return None, "no_price_evidence"
    if not candidates:
        return None, "no_stated_ratio"
    best, error = None, None
    for factor in candidates:
        relative = abs(observed - factor) / factor
        if error is None or relative < error:
            best, error = factor, relative
    if error is not None and error <= tolerance:
        return best, "corroborated"
    if abs(observed - 1.0) <= no_gap_tolerance:
        return None, "series_already_adjusted"
    return None, "stated_ratio_contradicted_by_prices"


def resolve(
    prices: list[tuple[date, float]],
    actions: Iterable[dict[str, Any]],
    tolerance: float = TOLERANCE,
) -> dict[str, Any]:
    """Corroborated factors for one symbol, plus why each action was dropped.

    Actions sharing an ex-date are collapsed first: TRENT's bonus and split
    rows describe one event, and applying both would double-adjust.
    """
    by_date: dict[date, list[dict[str, Any]]] = {}
    reasons: dict[str, int] = {}
    for action in actions or []:
        when = _as_date(action.get("action_date") or action.get("ex_date"))
        if when:
            by_date.setdefault(when, []).append(action)

    factors: list[tuple[date, float]] = []
    detail: list[dict[str, Any]] = []
    for when in sorted(by_date, reverse=True):
        pooled: list[float] = []
        skipped: Optional[str] = None
        for action in by_date[when]:
            cands, reason = candidate_factors(action)
            pooled.extend(cands)
            if reason and not cands:
                skipped = reason
        seen = sorted({round(f, 6) for f in pooled})
        gap = observed_factor(prices, when)
        factor, status = reconcile(seen, gap, tolerance)
        if factor is None and skipped and not seen:
            status = skipped
        if factor is not None:
            factors.append((when, factor))
        reasons[status] = reasons.get(status, 0) + 1
        detail.append({
            "ex_date": when.isoformat(),
            "stated_candidates": seen,
            "observed_gap": round(gap, 6) if gap is not None else None,
            "applied": factor,
            "status": status,
        })

    return {"factors": factors, "detail": detail, "reasons": reasons,
            "quarantined": any(d["status"] == "stated_ratio_contradicted_by_prices"
                               for d in detail),
            # Vendor-adjusted history needs no factor and is not a defect.
            "already_adjusted": any(d["status"] == "series_already_adjusted"
                                    for d in detail)}


def build_factors(
    actions: Iterable[dict[str, Any]],
    prices_by_symbol: Optional[dict[str, list[tuple[date, float]]]] = None,
    tolerance: float = TOLERANCE,
) -> dict[str, list[tuple[date, float]]]:
    """Per-symbol corroborated (ex_date, factor), newest first.

    Without prices_by_symbol nothing can be corroborated, so nothing is
    returned. That is deliberate: the previous version applied whatever the
    ratio string said, and the ratio string is wrong about half the time.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for action in actions or []:
        symbol = str(action.get("symbol") or "").strip().upper()
        if symbol:
            grouped.setdefault(symbol, []).append(action)

    out: dict[str, list[tuple[date, float]]] = {}
    for symbol, rows in grouped.items():
        prices = (prices_by_symbol or {}).get(symbol) or []
        resolved = resolve(prices, rows, tolerance)
        if resolved["factors"]:
            out[symbol] = sorted(resolved["factors"], key=lambda r: r[0], reverse=True)
    return out


def adjust_series(
    prices: list[tuple[date, float]],
    factors: list[tuple[date, float]],
    drop_non_trading_days: bool = True,
) -> list[tuple[date, float]]:
    """Restate a price series onto the current share base.

    Weekend rows are dropped by default. They are not merely redundant - they
    carry a differently scaled series, so keeping them fabricates enormous
    round-trip moves that no strategy actually traded.
    """
    if not prices:
        return []
    rows = [(d, p) for d, p in prices if p and p > 0]
    if drop_non_trading_days:
        rows = [(d, p) for d, p in rows if is_trading_day(d)]
    out: list[tuple[date, float]] = []
    for when, price in sorted(rows, key=lambda r: r[0]):
        cumulative = 1.0
        for ex_date, factor in factors or []:
            if ex_date > when:
                cumulative *= factor
        out.append((when, price * cumulative))
    return out


def monthly_returns(series: list[tuple[date, float]]) -> list[tuple[date, float]]:
    ordered = sorted(series, key=lambda p: p[0])
    out: list[tuple[date, float]] = []
    for (_, prev), (when, curr) in zip(ordered, ordered[1:]):
        if prev and prev > 0:
            out.append((when, curr / prev - 1.0))
    return out


def audit(
    actions: Iterable[dict[str, Any]],
    prices_by_symbol: Optional[dict[str, list[tuple[date, float]]]] = None,
) -> dict[str, Any]:
    """The CORPORATE_ACTION_UNVERIFIED receipt.

    Without prices this can only report what the action table claims, and says
    so; corroboration is impossible and no factor is trustworthy.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for action in actions or []:
        symbol = str(action.get("symbol") or "").strip().upper()
        if symbol:
            grouped.setdefault(symbol, []).append(action)

    reasons: dict[str, int] = {}
    applied = quarantined = already = 0
    for symbol, rows in grouped.items():
        resolved = resolve((prices_by_symbol or {}).get(symbol) or [], rows)
        applied += len(resolved["factors"])
        quarantined += int(resolved["quarantined"])
        already += int(resolved.get("already_adjusted", False))
        for key, count in resolved["reasons"].items():
            reasons[key] = reasons.get(key, 0) + count

    corroborated = prices_by_symbol is not None
    return {
        "ok": True,
        "corroborated_against_prices": corroborated,
        "actions_seen": sum(len(v) for v in grouped.values()),
        "symbols": len(grouped),
        "adjustments_applied": applied,
        "symbols_quarantined": quarantined,
        "symbols_already_adjusted": already,
        "breakdown": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "status": "CORROBORATED" if corroborated else "UNVERIFIABLE_WITHOUT_PRICES",
        "limitations": [
            "A series the vendor already adjusted shows no gap at its ex-dates and "
            "needs no factor; that is reported as series_already_adjusted, not as a "
            "contradiction. The Upstox backfill delivers pre-adjusted candles, so "
            "this is now the expected state for most symbols.",
            "Stated split ratios are unreliable: of 45 structural actions measured "
            "against the price series, 19 matched a/b, 2 matched b/a, 3 showed no "
            "price gap, and the rest matched neither reading.",
            "Adjustments are applied only where the observed price gap corroborates "
            "the stated ratio; contradicted symbols are quarantined, not guessed.",
            "Rights issues are not adjusted: subscription price and take-up are absent.",
            "Dividends are not reinvested, so this is a price-return series.",
            "warehouse adjusted_close equals close wherever populated and reflects "
            "no structural action, so it is ignored.",
            "Weekend rows (about 18% of daily_market_history) are dropped as "
            "non-trading days; they carry a differently scaled series.",
        ],
    }
