"""Admin workbook: one sheet per ratio, companies down column A, dates across.

The warehouse stores ``valuation_ratios`` long - one row per (symbol,
ratio_name, reported_date, snapshot_id). That shape answers "what is
RELIANCE's P/E today" and is wrong for the question the desk actually asks,
which is "show me every company's P/E and how it has moved". Pivoting 62k+
rows by hand in Excel is the sort of thing that gets done once and then
silently goes stale, so it is built here instead.

Sheets are the six ratios Upstox reports, plus a coverage sheet. Six ratios
is not a design choice - it is what ``/v2/fundamentals/{isin}/key-ratios``
returns, and inventing a seventh would mean inventing the data behind it.

Dates run newest-first from column D. A year of daily collection is 250
columns; appending on the right would mean scrolling to the far edge of the
sheet to see today. The sheet is rebuilt from the warehouse on each request
rather than incrementally appended, because the warehouse is the record and a
workbook that drifts from it is worse than no workbook.

Every company in the eligible universe gets a row even when it has no data.
An admin sheet exists to show gaps; dropping the empty rows would hide exactly
the companies worth looking at.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from valuation_ratios.sweep import ELIGIBLE_EQUITY, EXPECTED, classify

# Display names. The tab label is what an admin reads, so "P/E" rather than
# "pe" - but "/" is illegal in an Excel sheet name, hence the spelled forms.
SHEET_TITLES: dict[str, str] = {
    "pe": "P-E",
    "pb": "P-B",
    "roa": "ROA",
    "roe": "ROE",
    "roce": "ROCE",
    "ev_ebitda": "EV-EBITDA",
}

COVERAGE_SHEET = "Coverage"
IDENTITY_HEADERS = ("Symbol", "Company", "Sector")
DEFAULT_DAYS = 120
MAX_DAYS = 750


def _physical() -> str:
    from institutional_warehouse import db

    return db.physical_table("valuation_ratios")


def _universe() -> list[dict[str, Any]]:
    """Eligible equities from the master, plus anything that already has rows.

    The second half matters: a symbol can carry ratios collected before the
    classifier learned to read it, and dropping it here would quietly shrink
    the sheet relative to the warehouse it is supposed to mirror.
    """
    from institutional_warehouse import db, store

    known: dict[str, dict[str, Any]] = {}
    for row in store.all_rows("company_master", limit=20000) or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        known[symbol] = {
            "symbol": symbol,
            "company": str(row.get("company_name") or "").strip(),
            "sector": str(row.get("sector") or "").strip(),
            "isin": str(row.get("isin") or "").strip().upper(),
            "eligible": classify(row) == ELIGIBLE_EQUITY,
        }

    with_rows = {
        str(r.get("symbol") or "").strip().upper()
        for r in db.query(f"SELECT DISTINCT symbol FROM {_physical()}")
    }
    out = [c for c in known.values() if c["eligible"] or c["symbol"] in with_rows]
    for symbol in sorted(with_rows - set(known)):
        if symbol:
            out.append({"symbol": symbol, "company": "", "sector": "",
                        "isin": "", "eligible": False})
    out.sort(key=lambda c: c["symbol"])
    return out


def recent_dates(days: int) -> list[str]:
    """The most recent N collection dates, newest first.

    Dates come from the data rather than from a calendar. A market holiday is
    not a missing column, and back-dating a column the sweep never ran would
    turn "we did not collect" into "we collected nothing", which are different
    facts.
    """
    from institutional_warehouse import db

    rows = db.query(
        f"SELECT DISTINCT reported_date AS d FROM {_physical()} "
        "WHERE reported_date IS NOT NULL AND reported_date <> '' "
        "ORDER BY d DESC"
    )
    dates = [str(r["d"]) for r in rows if str(r.get("d") or "").strip()]
    return dates[:days]


def _values(dates: list[str]) -> dict[tuple[str, str, str], float]:
    """(symbol, ratio, date) -> company value, latest snapshot wins.

    The natural key carries ``snapshot_id``, so a day re-swept holds more than
    one row per company and ratio. Ordering by reported_time then snapshot_id
    and letting the last write win means the sheet shows the most recent
    reading rather than whichever row the database happened to return first.
    """
    from institutional_warehouse import db

    if not dates:
        return {}
    placeholders = ",".join(["?"] * len(dates))
    # "?" on both backends: db._bind rewrites it to named binds for
    # SQLAlchemy, so writing dialect-specific placeholders here would break
    # Postgres rather than support it.
    sql = (
        "SELECT symbol, ratio_name, reported_date, company_value "
        f"FROM {_physical()} WHERE reported_date IN ({placeholders}) "
        "ORDER BY reported_time ASC, snapshot_id ASC"
    )

    out: dict[tuple[str, str, str], float] = {}
    for row in db.query(sql, tuple(dates)):
        value = row.get("company_value")
        if value is None:
            continue
        key = (
            str(row.get("symbol") or "").strip().upper(),
            str(row.get("ratio_name") or "").strip().lower(),
            str(row.get("reported_date") or ""),
        )
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _autofilter(sheet, rows: int, cols: int) -> None:
    from openpyxl.utils import get_column_letter

    sheet.freeze_panes = "D2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(max(cols, 1))}{max(rows, 1)}"
    sheet.column_dimensions["A"].width = 16
    sheet.column_dimensions["B"].width = 38
    sheet.column_dimensions["C"].width = 22


def build(*, days: int = DEFAULT_DAYS) -> tuple[Any, dict[str, Any]]:
    """Return (workbook, summary). Summary is what the route reports as headers."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    days = max(1, min(int(days or DEFAULT_DAYS), MAX_DAYS))
    universe = _universe()
    dates = recent_dates(days)
    values = _values(dates)

    workbook = Workbook()
    workbook.remove(workbook.active)
    header_font = Font(bold=True)
    tilted = Alignment(textRotation=60, horizontal="center")

    for ratio in EXPECTED:
        sheet = workbook.create_sheet(SHEET_TITLES[ratio])
        sheet.append(list(IDENTITY_HEADERS) + list(dates))
        for index, cell in enumerate(sheet[1], start=1):
            cell.font = header_font
            if index > len(IDENTITY_HEADERS):
                cell.alignment = tilted
        for company in universe:
            symbol = company["symbol"]
            sheet.append(
                [symbol, company["company"], company["sector"]]
                + [values.get((symbol, ratio, day)) for day in dates]
            )
        for column in range(len(IDENTITY_HEADERS) + 1, len(IDENTITY_HEADERS) + len(dates) + 1):
            sheet.column_dimensions[get_column_letter(column)].width = 11
        _autofilter(sheet, len(universe) + 1, len(IDENTITY_HEADERS) + len(dates))

    latest = dates[0] if dates else None
    coverage = workbook.create_sheet(COVERAGE_SHEET)
    coverage.append(
        list(IDENTITY_HEADERS)
        + ["ISIN", "Eligible", "Days Collected", "First Date", "Latest Date",
           "Ratios On Latest Date"]
        + [f"Latest {SHEET_TITLES[r]}" for r in EXPECTED]
    )
    for cell in coverage[1]:
        cell.font = header_font

    for company in universe:
        symbol = company["symbol"]
        present = [d for d in dates
                   if any((symbol, r, d) in values for r in EXPECTED)]
        on_latest = sum(1 for r in EXPECTED if (symbol, r, latest) in values) if latest else 0
        latest_each = []
        for ratio in EXPECTED:
            # First hit walking newest-first is the most recent reading, which
            # is not the same as the value on the latest date - a ratio missing
            # today still has a last known value, and blanking it would report
            # a collection gap as an absent ratio.
            latest_each.append(next(
                (values[(symbol, ratio, d)] for d in dates
                 if (symbol, ratio, d) in values), None))
        coverage.append(
            [symbol, company["company"], company["sector"], company["isin"],
             "yes" if company["eligible"] else "no", len(present),
             present[-1] if present else None, present[0] if present else None,
             on_latest]
            + latest_each
        )
    _autofilter(coverage, len(universe) + 1, 9 + len(EXPECTED))
    coverage.freeze_panes = "D2"

    covered = sum(
        1 for c in universe
        if latest and any((c["symbol"], r, latest) in values for r in EXPECTED)
    )
    summary = {
        "companies": len(universe),
        "dates": len(dates),
        "latest_date": latest,
        "oldest_date": dates[-1] if dates else None,
        "values": len(values),
        "companies_on_latest_date": covered,
        "sheets": [SHEET_TITLES[r] for r in EXPECTED] + [COVERAGE_SHEET],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return workbook, summary


def build_bytes(*, days: int = DEFAULT_DAYS) -> tuple[bytes, dict[str, Any]]:
    """Serialise to memory. The engine has no writable disk it should rely on."""
    import io

    workbook, summary = build(days=days)
    buffer = io.BytesIO()
    workbook.save(buffer)
    payload = buffer.getvalue()
    summary["bytes"] = len(payload)
    return payload, summary


def filename(summary: Optional[dict[str, Any]] = None) -> str:
    stamp = (summary or {}).get("latest_date") or datetime.now(timezone.utc).date().isoformat()
    return f"agi_valuation_ratios_{stamp}.xlsx"
