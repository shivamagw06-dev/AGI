"""One identity for a reporting period, whatever the vendor called it.

RELIANCE's June 2026 quarter is stored four times. Upstox calls it ``FY2027Q1``,
one importer calls it ``FY27Q1``, another calls it ``Q1 FY27``, and the detector
sees ``Jun 2026``. Compared as strings none of them match, so the same three
months occupy four rows, a refresh cannot find what it wrote yesterday, and
anything reading "the latest quarter" picks whichever row sorted first.

The fix is not to declare one spelling correct and rewrite the others. Rewriting
a label that sits in the natural key changes the row id, which forks history
rather than merging it - and the Capital IQ decade is keyed on those labels.

So every row carries a ``period_key`` alongside whatever it calls itself: the
first day of the month *after* the period ends. That convention comes from
:func:`parse_period` and exists so two labels for one period compare equal
instead of landing a day apart. Grouping by it collapses the four spellings
without touching a single stored label.

Indian fiscal years end in March. FY2026 runs April 2025 to March 2026, and its
Q1 is the June quarter of calendar 2025 - which is why naive year arithmetic on
these labels has been wrong every time it has been attempted here.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

#: Tabs whose rows are reporting periods rather than observations.
FUNDAMENTAL_TABS: frozenset[str] = frozenset({"financials_annual", "financials_quarterly"})

#: Which label column carries the period, per tab.
PERIOD_FIELD: dict[str, str] = {
    "financials_annual": "fiscal_year",
    "financials_quarterly": "fiscal_period",
}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

#: Month a fiscal quarter ends in, for a March year-end.
_QUARTER_END_MONTH = {1: 6, 2: 9, 3: 12, 4: 3}
_MONTH_QUARTER = {m: q for q, m in _QUARTER_END_MONTH.items()}


def _month_end(year: int, month: int) -> date:
    """The day a period ends, expressed as the first of the next month.

    A single convention throughout, so two labels for the same period compare
    equal rather than one day apart.
    """
    return date(year + (month == 12), 1 if month == 12 else month + 1, 1)


def parse_period(raw: Any) -> Optional[date]:
    """Any period label this warehouse actually contains, as a date.

    Handles every format the live data holds at once: ``2026-03-31``,
    ``Mar 2026``, ``FY2026``, ``FY26``, ``FY2026Q3``, ``FY26Q3``, ``Q3 FY2026``.
    """
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        exact = datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    else:
        # A real filing date sits on the last day of the period; the marker
        # convention is the first of the month after. Without this fold,
        # "2026-06-30" and "Jun 2026" describe the same quarter and still fail
        # to compare equal, which is the whole defect this module exists for.
        if exact.day == 1:
            return exact
        return _month_end(exact.year, exact.month)

    month_year = re.match(r"^([A-Za-z]{3})[a-z]*\s+(\d{4})$", text)
    if month_year:
        month = _MONTHS.get(month_year.group(1).lower())
        return _month_end(int(month_year.group(2)), month) if month else None

    quarter = (re.match(r"^FY\s*(\d{2,4})\s*Q([1-4])$", text, re.I)
               or re.match(r"^Q([1-4])\s*FY\s*(\d{2,4})$", text, re.I))
    if quarter:
        groups = quarter.groups()
        if text.upper().startswith("Q"):
            qtr, year_raw = int(groups[0]), groups[1]
        else:
            year_raw, qtr = groups[0], int(groups[1])
        year = int(year_raw)
        if year < 100:
            year += 2000
        # Q1 of FY2026 is the June quarter of calendar 2025.
        month = _QUARTER_END_MONTH[qtr]
        return _month_end(year if qtr == 4 else year - 1, month)

    fiscal = re.match(r"^FY\s*(\d{2,4})$", text, re.I)
    if fiscal:
        year = int(fiscal.group(1))
        if year < 100:
            year += 2000
        return _month_end(year, 3)

    return None


def period_key(raw: Any) -> Optional[str]:
    """The grouping identity for a period label, or None if it will not parse.

    Two rows share a key exactly when they describe the same months, regardless
    of which of the four spellings each one used.
    """
    when = parse_period(raw)
    return when.isoformat() if when else None


def _ended(marker: date) -> tuple[int, int]:
    """Calendar (year, month) a period ending at this marker actually ended in."""
    return (marker.year, 12) if marker.month == 1 else (marker.year, marker.month - 1)


def canonical_label(raw: Any, *, tab_id: str) -> Optional[str]:
    """The one spelling this warehouse writes, for a canonical source.

    ``FY2027Q1`` for quarters and ``FY2026`` for years - four digits always,
    because ``FY26`` and ``FY2026`` are the pair that forked the annual tab.

    Returns None for a period that will not parse, and for a quarter that does
    not end in March, June, September or December: a company on a non-March
    year-end has no standard fiscal quarter number, and inventing one would put
    a real filing under a label that means something else.
    """
    marker = parse_period(raw)
    if marker is None:
        return None
    year, month = _ended(marker)

    if tab_id == "financials_annual":
        # A fiscal year is named for the calendar year it ends in, and it ends
        # in March. A period ending in any other month is that year's filing
        # only if we treat April-December as belonging to the year ahead.
        return f"FY{year if month <= 3 else year + 1}"

    quarter = _MONTH_QUARTER.get(month)
    if quarter is None:
        return None
    return f"FY{year if quarter == 4 else year + 1}Q{quarter}"


def stamp(tab_id: str, rows: Any, *, canonicalise_label: bool = False) -> list[dict[str, Any]]:
    """Add ``period_key`` to each row, and optionally fix its label.

    The key is always added - it is new information and collides with nothing.
    The label is rewritten only for a source allowed to write canonical rows,
    because the label is part of the natural key: changing it on a legacy row
    would mint a new row id and duplicate the period rather than merge it.
    """
    if tab_id not in FUNDAMENTAL_TABS:
        return list(rows or [])
    field = PERIOD_FIELD[tab_id]

    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        new_row = dict(row)
        raw = new_row.get(field)
        key = period_key(raw)
        if key:
            new_row["period_key"] = key
        if canonicalise_label:
            label = canonical_label(raw, tab_id=tab_id)
            if label:
                new_row[field] = label
        out.append(new_row)
    return out
