"""Period normalisation.

Historical series are labelled two different ways: market data by ISO date, and
statements by fiscal label (``FY07``, ``FY24Q2``). The span guard has to compare
both against a question's asked window, so every label resolves to a comparable
date here.

Getting this wrong is not cosmetic. Before it existed, "revenue since 2005"
against a series running FY07 to FY26 computed a zero overlap and the engine
declined a question it could largely answer.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from institutional_warehouse.values import to_date

_FY = re.compile(r"^FY\s?(\d{2}|\d{4})(?:\s?(Q[1-4]))?$", re.IGNORECASE)
_Q_FIRST = re.compile(r"^(Q[1-4])\s?FY\s?(\d{2}|\d{4})$", re.IGNORECASE)

# Indian fiscal year ends 31 March: FY07 covers Apr 2006 to Mar 2007.
_QUARTER_ENDS = {"Q1": (-1, 6, 30), "Q2": (-1, 9, 30), "Q3": (-1, 12, 31), "Q4": (0, 3, 31)}


def _fiscal_year(raw: str) -> int:
    value = int(raw)
    return value if value > 1900 else 2000 + value


def period_end(label: str) -> Optional[str]:
    """The calendar date a period label ends on. ISO dates pass straight through."""
    text = str(label or "").strip()
    if not text:
        return None

    direct = to_date(text)
    if direct:
        return direct

    match = _FY.match(text) or None
    quarter = None
    if match:
        year = _fiscal_year(match.group(1))
        quarter = (match.group(2) or "").upper() or None
    else:
        flipped = _Q_FIRST.match(text)
        if not flipped:
            return None
        quarter = flipped.group(1).upper()
        year = _fiscal_year(flipped.group(2))

    if not quarter:
        return date(year, 3, 31).isoformat()
    offset, month, day = _QUARTER_ENDS[quarter]
    return date(year + offset, month, day).isoformat()


def period_start(label: str) -> Optional[str]:
    """The date a period label begins on, used for the earliest observation."""
    text = str(label or "").strip()
    direct = to_date(text)
    if direct:
        return direct
    end = period_end(text)
    if not end:
        return None
    match = _FY.match(text) or _Q_FIRST.match(text)
    if not match:
        return end
    is_quarter = "Q" in text.upper()
    ending = date.fromisoformat(end)
    if is_quarter:
        month = ending.month - 2
        year = ending.year if month > 0 else ending.year - 1
        month = month if month > 0 else month + 12
        return date(year, month, 1).isoformat()
    return date(ending.year - 1, 4, 1).isoformat()


def comparable(label: str) -> Optional[str]:
    """A single date any period can be ordered and compared by."""
    return period_end(label)


def is_fiscal_label(label: str) -> bool:
    text = str(label or "").strip()
    return bool(_FY.match(text) or _Q_FIRST.match(text))
