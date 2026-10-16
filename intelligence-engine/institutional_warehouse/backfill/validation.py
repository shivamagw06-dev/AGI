"""Time-series screening for the backfill.

The warehouse validator judges a row on its own terms. A historical series needs
two more questions asked of it: is the chronology sound, and does this
observation make sense next to the one before it?

Reject   impossible prices, broken chronology, duplicate dates, future dates,
         invalid symbols
Warn     extreme single-day returns, extreme multiples, corporate-action
         anomalies (a price break with no split on record)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse.validation import SYMBOL_RE
from institutional_warehouse.values import to_date, to_number

# A stock can double or halve in a day; an order-of-magnitude move without a
# corporate action is a data break, not a market event.
EXTREME_RETURN_PCT = 60.0
SPLIT_SUSPECT_RATIO = 1.8


def _issue(level: str, code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"level": level, "code": code, "message": message, **extra}


def screen_series(
    rows: Sequence[dict[str, Any]],
    *,
    date_field: str = "date",
    price_field: str = "close",
    known_actions: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    """Screen an ordered price series. Returns accepted rows plus findings."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    action_dates = {str(d) for d in (known_actions or [])}

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous: Optional[dict[str, Any]] = None

    ordered = sorted(
        [r for r in rows if r.get(date_field)],
        key=lambda r: str(to_date(r.get(date_field)) or ""),
    )

    for row in ordered:
        observed = to_date(row.get(date_field))
        symbol = str(row.get("symbol") or "").upper()
        issues: list[dict[str, Any]] = []

        if not observed:
            issues.append(_issue("error", "invalid_date", f"unparseable date {row.get(date_field)!r}"))
        elif observed > tomorrow:
            issues.append(_issue("error", "future_date", f"{observed} is in the future"))
        elif observed in seen:
            issues.append(_issue("error", "duplicate_date", f"{observed} already present in this series"))

        if symbol and not SYMBOL_RE.match(symbol):
            issues.append(_issue("error", "invalid_symbol", f"{symbol!r} is not a valid ticker"))

        close = to_number(row.get(price_field))
        if close is None:
            issues.append(_issue("error", "missing_price", "no close price"))
        elif close <= 0:
            issues.append(_issue("error", "impossible_price", f"close {close} is not positive"))

        high, low = to_number(row.get("high")), to_number(row.get("low"))
        if high is not None and low is not None and low > high:
            issues.append(_issue("error", "impossible_range", f"low {low} above high {high}"))
        if close is not None and high is not None and low is not None and not (low <= close <= high):
            issues.append(_issue("warn", "close_outside_range", f"close {close} outside [{low}, {high}]"))

        volume = to_number(row.get("volume"))
        if volume is not None and volume < 0:
            issues.append(_issue("error", "impossible_volume", f"volume {volume} is negative"))

        if previous and close and to_number(previous.get(price_field)):
            prior = to_number(previous[price_field])
            change = 100.0 * (close - prior) / prior
            if abs(change) >= EXTREME_RETURN_PCT:
                ratio = max(close, prior) / min(close, prior)
                if ratio >= SPLIT_SUSPECT_RATIO and observed not in action_dates:
                    issues.append(
                        _issue("warn", "unexplained_price_break",
                               f"{round(change, 1)}% move on {observed} with no corporate action on record")
                    )
                else:
                    issues.append(_issue("warn", "extreme_return",
                                         f"{round(change, 1)}% move on {observed}"))

        errors = [i for i in issues if i["level"] == "error"]
        warns = [i for i in issues if i["level"] == "warn"]
        if warns:
            warnings.append({"date": observed, "symbol": symbol, "issues": warns})
        if errors:
            rejected.append({"date": observed, "symbol": symbol, "issues": errors})
            continue

        seen.add(observed)
        accepted.append(row)
        previous = row

    return {
        "ok": not rejected,
        "seen": len(ordered),
        "accepted": accepted,
        "accepted_count": len(accepted),
        "rejected": rejected,
        "rejected_count": len(rejected),
        "warnings": warnings,
        "warning_count": len(warnings),
    }


def chronology_report(
    rows: Sequence[dict[str, Any]],
    *,
    date_field: str = "date",
    max_gap_days: int = 10,
) -> dict[str, Any]:
    """Describe the shape of a stored series: span, density and its largest holes."""
    dates = sorted({to_date(r.get(date_field)) for r in rows if to_date(r.get(date_field))})
    if not dates:
        return {"ok": True, "points": 0, "gaps": [], "first": None, "last": None, "years": 0.0}

    gaps: list[dict[str, Any]] = []
    for earlier, later in zip(dates, dates[1:]):
        delta = (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).days
        if delta > max_gap_days:
            gaps.append({"from": earlier, "to": later, "days": delta})

    span_days = (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])).days
    return {
        "ok": True,
        "points": len(dates),
        "first": dates[0],
        "last": dates[-1],
        "years": round(span_days / 365.25, 2),
        "gaps": sorted(gaps, key=lambda g: g["days"], reverse=True)[:20],
        "gap_count": len(gaps),
    }
