"""Temporal detection — as_of / relative windows inherited by IERE and Ask."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any


_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_AS_OF = re.compile(r"\bas of\s+([0-9]{1,2}\s+\w+\s+20\d{2}|20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/20\d{2})\b", re.I)
_YEAR = re.compile(r"\b(?:in|during|year)\s+(20\d{2})\b", re.I)
_FY = re.compile(r"\bfy\s?((?:20)?\d{2})\b", re.I)
_BEFORE_COVID = re.compile(r"\bbefore covid\b|\bpre[- ]covid\b", re.I)
_LAST_QUARTER = re.compile(r"\blast quarter\b|\bprior quarter\b|\bprevious quarter\b", re.I)
_TODAY = re.compile(r"\b(today|currently|right now|present(?:ly)?)\b", re.I)
_LAST_DECADE = re.compile(r"\blast decade\b|\bpast 10 years\b|\bover the last (?:ten|10) years\b", re.I)
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def detect_temporal(question: str, *, today: date | None = None) -> dict[str, Any]:
    q = str(question or "").strip()
    ql = q.lower()
    today = today or datetime.now(timezone.utc).date()

    as_of: str | None = None
    mode = "current"
    relative: str | None = None
    reasons: list[str] = []

    m_iso = _ISO.search(q)
    if m_iso:
        as_of = f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"
        mode = "point_in_time"
        reasons.append("iso_date")

    if not as_of:
        m_as = _AS_OF.search(q)
        if m_as:
            parsed = _parse_human_date(m_as.group(1))
            if parsed:
                as_of = parsed
                mode = "point_in_time"
                reasons.append("as_of_phrase")

    if not as_of and _BEFORE_COVID.search(ql):
        as_of = "2020-03-01"
        mode = "point_in_time"
        reasons.append("before_covid")

    if not as_of:
        m_fy = _FY.search(ql)
        if m_fy:
            raw = m_fy.group(1)
            year = int(raw) if len(raw) == 4 else 2000 + int(raw)
            # Indian FY ends 31 March of the FY label year (FY19 → 2019-03-31).
            as_of = f"{year}-03-31"
            mode = "point_in_time"
            reasons.append("fiscal_year")

    if not as_of:
        m_year = _YEAR.search(ql)
        if m_year:
            as_of = f"{m_year.group(1)}-12-31"
            mode = "point_in_time"
            reasons.append("calendar_year")

    if _LAST_QUARTER.search(ql):
        relative = "last_quarter"
        mode = "relative" if not as_of else mode
        reasons.append("last_quarter")
        if not as_of:
            # Approximate prior calendar quarter end
            qtr = (today.month - 1) // 3
            if qtr == 0:
                as_of = f"{today.year - 1}-12-31"
            else:
                end_month = qtr * 3
                # last day approx
                as_of = f"{today.year}-{end_month:02d}-28"
            mode = "point_in_time"

    if _LAST_DECADE.search(ql):
        relative = "last_decade"
        reasons.append("last_decade")
        if mode == "current":
            # Range cue only — do not invent a point-in-time as_of for IERE replay.
            mode = "range"

    if _TODAY.search(ql) and mode == "current":
        relative = "today"
        reasons.append("today_current")
        as_of = today.isoformat()

    # Replay verbs without date still mark historical mode
    if re.search(r"\breplay\b", ql) and mode == "current":
        mode = "historical_replay_request"
        reasons.append("replay_verb")

    return {
        "mode": mode,
        "as_of": as_of,
        "relative": relative,
        "is_historical": mode in {"point_in_time", "historical_replay_request", "range"}
        or bool(re.search(r"\breplay\b", ql)),
        "reasons": reasons,
        "fabricated": False,
    }


def _parse_human_date(raw: str) -> str | None:
    s = raw.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(20\d{2})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Prefer DMY for institutional India wording
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            try:
                return date(y, d, mo).isoformat()
            except ValueError:
                return None
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})$", s)
    if m:
        d = int(m.group(1))
        mo = _MONTHS.get(m.group(2).lower())
        y = int(m.group(3))
        if mo:
            try:
                return date(y, mo, d).isoformat()
            except ValueError:
                return None
    return None
