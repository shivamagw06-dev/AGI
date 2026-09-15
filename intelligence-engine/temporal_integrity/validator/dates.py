"""Deterministic date helpers for temporal integrity."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_ISO_RE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def as_of_year(as_of: Any) -> int | None:
    d = parse_date(as_of)
    return d.year if d else None


def years_in_text(text: Any) -> list[int]:
    return [int(m.group(0)) for m in _YEAR_RE.finditer(str(text or ""))]


def period_end_year(period: Any) -> int | None:
    """Extract the latest year mentioned in a time_period string."""
    years = years_in_text(period)
    return max(years) if years else None


def available_from_of(obj: dict[str, Any]) -> date | None:
    for key in (
        "available_from",
        "effective_date",
        "announcement_date",
        "observation_date",
        "source_timestamp",
        "as_of",
        "date",
    ):
        d = parse_date(obj.get(key))
        if d is not None:
            return d
    return None


def violates_available_from(obj: dict[str, Any], as_of: Any) -> bool:
    cutoff = parse_date(as_of)
    if cutoff is None:
        return False
    af = available_from_of(obj)
    if af is None:
        return False
    return af > cutoff


def text_has_future_year(text: Any, as_of: Any) -> bool:
    y = as_of_year(as_of)
    if y is None:
        return False
    return any(yr > y for yr in years_in_text(text))


def redact_future_years(text: str, as_of: Any) -> str:
    """Redact year tokens strictly after as_of year (for display sanitisation logs only)."""
    y = as_of_year(as_of)
    if y is None:
        return text

    def _sub(m: re.Match[str]) -> str:
        yr = int(m.group(0))
        return "[REDACTED_FUTURE_YEAR]" if yr > y else m.group(0)

    return _YEAR_RE.sub(_sub, text)
