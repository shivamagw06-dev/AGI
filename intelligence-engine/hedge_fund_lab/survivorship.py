"""Measure how much of the past universe is missing from the warehouse.

Every backtest here ranks companies that are listed today. Companies that were
delisted along the way were never collected, so a strategy tested in 2020 picks
from a list that quietly excludes everything which later failed. That is
survivorship bias, and until now its size was unknown - not even roughly.

The NSE delisted-companies list closes that gap. It does not carry prices, so
it cannot correct a backtest. It carries names and dates, which is enough to
count what is absent and say how much of the universe that was.

The reason for delisting matters more than the count. A company that chose to
leave the exchange usually paid its shareholders to go; a company thrown off or
wound up usually did not. The second group is the one a ranked long portfolio
would have held into a loss, so failures are counted separately rather than
lumped in with buyouts.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

DELISTING_FILE = (Path(__file__).resolve().parents[2]
                  / "List_of_delisted_Companies_20260612152719(delisted).csv")
# The export is not UTF-8; it carries non-breaking spaces in company names.
FILE_ENCODING = "latin-1"

_DATE_FORMATS = ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y")

# A shareholder in a compulsory delisting or a liquidation usually loses most of
# the position. A voluntary exit is normally a buyout at a premium. Only the
# first kind makes a backtest look better than reality.
FAILURE_MARKERS = ("compulsory", "liquidation", "operation of law")
VOLUNTARY_MARKERS = ("voluntary", "exit from itp")


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def categorise(reason: Any) -> str:
    """Failure, voluntary, or other. Unknown reasons are never called failures."""
    text = str(reason or "").strip().lower()
    if any(marker in text for marker in FAILURE_MARKERS):
        return "failure"
    if any(marker in text for marker in VOLUNTARY_MARKERS):
        return "voluntary"
    return "other"


def load_delistings(path: Path = DELISTING_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding=FILE_ENCODING, newline="") as handle:
        for row in csv.DictReader(handle):
            when = _parse_date(row.get("Delisted Date"))
            symbol = str(row.get("Symbol") or "").strip().upper()
            if not when or not symbol:
                continue
            out.append({
                "symbol": symbol,
                "isin": str(row.get("ISIN") or "").strip().upper() or None,
                "name": str(row.get("Company Name") or "").strip(),
                "delisted_on": when.isoformat(),
                "reason": str(row.get("Type of Delisting") or "").strip(),
                "category": categorise(row.get("Type of Delisting")),
            })
    return out


def _month_end(month: str) -> Optional[date]:
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        return None
    return date(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)


def missing_at(month: str, delistings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Companies still trading in this month that the warehouse no longer holds.

    The backtest ranks at month end and holds to the next, so a company counts
    as missing only if it was still listed at that ranking date. One delisted
    on 31 March could not have been bought in March; it is missing from
    February and earlier.
    """
    boundary = _month_end(month)
    if boundary is None:
        return []
    out = []
    for row in delistings or []:
        when = _parse_date(row.get("delisted_on"))
        if when and when >= boundary:
            out.append(row)
    return out


def bias_report(
    universe_by_month: dict[str, int],
    delistings: Optional[Iterable[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """How much of each month's real universe the warehouse cannot see.

    `universe_by_month` is how many companies the backtest actually ranked in
    that month. The missing count is added to it to estimate the universe that
    existed at the time.
    """
    rows = list(delistings if delistings is not None else load_delistings())
    if not rows:
        return {"ok": False, "error": "no_delisting_data"}

    months = sorted(universe_by_month or {})
    periods = []
    for month in months:
        held = int(universe_by_month.get(month) or 0)
        gone = missing_at(month, rows)
        failures = [g for g in gone if g["category"] == "failure"]
        true_universe = held + len(gone)
        periods.append({
            "month": month,
            "ranked_by_backtest": held,
            "missing": len(gone),
            "missing_failures": len(failures),
            "estimated_true_universe": true_universe,
            "missing_share_pct": round(100.0 * len(gone) / true_universe, 2) if true_universe else None,
        })

    worst = max(periods, key=lambda p: p["missing"]) if periods else None
    latest = periods[-1] if periods else None
    return {
        "ok": True,
        "months": len(periods),
        "delistings_loaded": len(rows),
        "by_category": {
            c: sum(1 for r in rows if r["category"] == c)
            for c in ("failure", "voluntary", "other")
        },
        "worst_month": worst,
        "latest_month": latest,
        "periods": periods,
        "reading": (
            f"At the start of the window the backtest could not see "
            f"{periods[0]['missing']} companies that were still trading, "
            f"{periods[0]['missing_failures']} of which were later forced off the "
            f"exchange or wound up. Those are the losses a ranked long portfolio "
            f"never had to take."
            if periods else "no months supplied"
        ),
        "limitations": [
            "This measures the size of the gap. It does not close it: the list "
            "carries no prices, so a backtest still cannot hold these companies "
            "and take the loss.",
            "The NSE list covers companies removed from that exchange. Anything "
            "delisted only from BSE, or that stopped trading without a formal "
            "delisting, is still uncounted.",
            "A voluntary delisting is usually a buyout at a premium, so counting "
            "it as a missing loss would overstate the bias. Only compulsory "
            "removals and liquidations are treated as failures.",
        ],
    }
