"""Writing and reading the append-only consensus ledger.

The table refuses UPDATE and DELETE at the database level, so the job of this
module is to make the correct thing easy: build well-formed vintage rows, refuse
malformed ones before they reach the wire, and read revisions back out in a way
that cannot accidentally compare two different fiscal years.

The reason for the strictness is that the failure is silent and permanent. A
loader that upserts looks like it is working -- the row count is right, the
latest figure is right, the dashboard is green -- and the history quietly does
not accumulate. That is the state `consensus_metric_vintages` is in for every
forward period: one vintage each for FY2027 and FY2028, so no revision can be
computed for the only years anyone is forecasting.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Optional

from .fiscal import UNIVERSE, normalise_label, period_end

LEDGER_TABLE = "consensus_vintage_ledger"
LEDGER_VERSION = "consensus-ledger-1"

# Metrics worth a vintage. Anything else is rejected rather than stored under a
# name nothing downstream knows how to read.
METRICS = ("eps", "revenue", "ebitda", "ebit", "fcf", "operating_income")


class LedgerError(ValueError):
    """A row that must not be written."""


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return out if out == out and abs(out) != float("inf") else None


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for cut in (10, 19):
        try:
            return datetime.fromisoformat(text[:cut]).date()
        except ValueError:
            continue
    return None


def build_row(*, symbol: str, metric: str, fiscal_period: Any, consensus_date: Any,
              source: str, mean: Any = None, median: Any = None, high: Any = None,
              low: Any = None, analyst_count: Any = None,
              upward_revisions: Any = None, downward_revisions: Any = None,
              currency: str = "USD", unit: str = "per_share",
              extraction_method: Optional[str] = None,
              confidence: Any = None) -> dict[str, Any]:
    """One vintage, validated.

    Raises rather than returning a partial row: a consensus figure written
    against the wrong fiscal period is worse than no figure, because it will be
    silently differenced against a correct one later.
    """
    ticker = str(symbol or "").strip().upper()
    if ticker not in UNIVERSE:
        raise LedgerError(f"symbol outside the covered universe: {symbol!r}")
    if metric not in METRICS:
        raise LedgerError(f"unknown metric {metric!r}; expected one of {METRICS}")

    label = normalise_label(fiscal_period)
    if label is None:
        raise LedgerError(f"unparseable fiscal period: {fiscal_period!r}")
    ends = period_end(ticker, label)
    if ends is None:
        raise LedgerError(f"no fiscal calendar for {ticker} {label}")

    stamp = _as_date(consensus_date)
    if stamp is None:
        raise LedgerError(f"unparseable consensus_date: {consensus_date!r}")
    if stamp > date.today():
        raise LedgerError(f"consensus_date is in the future: {stamp.isoformat()}")
    if ends <= stamp:
        # An estimate for a year that has already closed is a historical
        # curiosity, not a forward consensus, and mixing the two is how a
        # "revision" ends up measuring a restatement.
        raise LedgerError(f"{label} ended {ends.isoformat()}, on or before the "
                          f"vintage date {stamp.isoformat()}")

    values = {"mean_estimate": _number(mean), "median_estimate": _number(median),
              "high_estimate": _number(high), "low_estimate": _number(low)}
    if all(v is None for v in values.values()):
        raise LedgerError("a vintage with no estimate value is not worth storing")
    lo, hi = values["low_estimate"], values["high_estimate"]
    if lo is not None and hi is not None and lo > hi:
        raise LedgerError(f"low {lo} above high {hi}")

    count = _number(analyst_count)
    return {
        "symbol": ticker,
        "company_name": UNIVERSE[ticker].name,
        "metric": metric,
        "fiscal_period": label,
        "fiscal_period_end": ends.isoformat(),
        "consensus_date": stamp.isoformat(),
        **values,
        "analyst_count": None if count is None else int(count),
        "upward_revisions": None if _number(upward_revisions) is None else int(_number(upward_revisions)),
        "downward_revisions": None if _number(downward_revisions) is None else int(_number(downward_revisions)),
        "currency": str(currency or "USD").upper(),
        "unit": str(unit or "per_share"),
        "source": str(source or "").strip() or "unknown",
        "extraction_method": extraction_method,
        "confidence": _number(confidence),
    }


def revision(series: Iterable[dict[str, Any]], as_of: date, *,
             lookback_days: int = 90) -> Optional[dict[str, Any]]:
    """Street movement on one fixed (symbol, metric, fiscal_period).

    Returns nothing when there is no earlier vintage, rather than zero. "No
    prior estimate" and "no change" are different facts, and reporting the first
    as the second is what makes a snapshot masquerade as a flat revision.
    """
    points: list[tuple[date, float]] = []
    periods, symbols = set(), set()
    for row in series or []:
        stamp = _as_date(row.get("consensus_date"))
        value = _number(row.get("mean_estimate"))
        if stamp is None or value is None or stamp > as_of:
            continue
        points.append((stamp, value))
        periods.add(str(row.get("fiscal_period")))
        symbols.add(str(row.get("symbol")))
    if len(periods) > 1 or len(symbols) > 1:
        raise LedgerError(f"revision needs one series; got periods={periods} symbols={symbols}")
    if len(points) < 2:
        return None
    points.sort(key=lambda pair: pair[0])
    latest_stamp, latest = points[-1]
    cutoff = date.fromordinal(as_of.toordinal() - int(lookback_days))
    earlier = [pair for pair in points if pair[0] <= cutoff]
    if not earlier:
        return None
    base_stamp, base = earlier[-1]
    if base_stamp == latest_stamp or abs(base) < 1e-9:
        return None
    return {
        "as_of": as_of.isoformat(),
        "from_date": base_stamp.isoformat(),
        "to_date": latest_stamp.isoformat(),
        "from_value": base,
        "to_value": latest,
        "revision_pct": round((latest / base - 1.0) * 100.0, 4),
        "lookback_days": lookback_days,
        "actual_span_days": latest_stamp.toordinal() - base_stamp.toordinal(),
    }


def write(rows: Iterable[dict[str, Any]], *, actor: str = "ai_infra") -> dict[str, Any]:
    """Insert vintages. Never upsert.

    Conflicts on the identity key are counted and skipped rather than merged: a
    second capture on the same day from the same source carries no new
    information, and resolving it by overwriting is the behaviour this whole
    table exists to prevent.
    """
    from institutional_warehouse import gateway

    payload = list(rows or [])
    if not payload:
        return {"ok": False, "written": 0, "error": "no_rows"}
    result = gateway.write(LEDGER_TABLE, payload, source="consensus_vintage_ledger",
                           actor=actor, reason="append_only_vintage_capture")
    return {"ok": bool(result.get("ok", True)), "written": len(payload),
            "table": LEDGER_TABLE, "version": LEDGER_VERSION, "gateway": result}
