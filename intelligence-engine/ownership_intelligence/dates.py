"""Shareholding period date helpers — never truncate DD-MMM-YYYY to 10 chars."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_nse_date(value: Any) -> str | None:
    """Normalize NSE dates to ISO YYYY-MM-DD."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s in {"-", "null", "None"}:
        return None
    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    # DD-MMM-YYYY or DD-MMM-YY
    m = re.match(r"^(\d{1,2})[-/ ]([A-Za-z]{3})[-/ ](\d{2,4})", s)
    if m:
        day = int(m.group(1))
        mon = _MONTHS.get(m.group(2).upper())
        year = int(m.group(3))
        if year < 100:
            year += 2000
        if mon:
            try:
                return datetime(year, mon, day).date().isoformat()
            except ValueError:
                return None
    # DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
        except ValueError:
            return None
    return None


def fiscal_quarter_label(iso_date: str | None) -> str | None:
    """Map period-end ISO date to Indian FY quarter label (FY ends March)."""
    if not iso_date:
        return None
    try:
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
    except ValueError:
        return None
    # Apr-Jun = Q1, Jul-Sep = Q2, Oct-Dec = Q3, Jan-Mar = Q4 of FY (year of March end)
    if dt.month in (4, 5, 6):
        q, fy = 1, dt.year + 1
    elif dt.month in (7, 8, 9):
        q, fy = 2, dt.year + 1
    elif dt.month in (10, 11, 12):
        q, fy = 3, dt.year + 1
    else:
        q, fy = 4, dt.year
    return f"Q{q} FY{str(fy)[2:]}"
