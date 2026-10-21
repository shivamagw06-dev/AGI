"""Period parsing and temporal windows for execution evaluation."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from management_execution.schema import WINDOWS


def parse_period_to_date(value: Any) -> date | None:
    """Map FY/Q labels or ISO dates to an approximate period-end date."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # ISO date
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = re.search(r"\bQ([1-4])\s*FY\s*'?(\d{2,4})\b", s, re.I)
    if m:
        q = int(m.group(1))
        yy = int(m.group(2))
        if yy < 100:
            yy += 2000
        # Indian FY: Q1 ends Jun, Q2 Sep, Q3 Dec, Q4 Mar(next)
        ends = {1: (yy - 1, 6, 30), 2: (yy - 1, 9, 30), 3: (yy - 1, 12, 31), 4: (yy, 3, 31)}
        y, mo, d = ends[q]
        return date(y, mo, d)
    m = re.search(r"\bFY\s*'?(\d{2,4})\b", s, re.I)
    if m:
        yy = int(m.group(1))
        if yy < 100:
            yy += 2000
        # Treat FY label as year ending 31 Mar of that calendar year
        return date(yy, 3, 31)
    m = re.search(r"\b(20\d{2})\b", s)
    if m:
        return date(int(m.group(1)), 12, 31)
    return None


def period_label(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"\b(Q[1-4]\s*FY\s*'?\d{2,4}|FY\s*'?\d{2,4})\b", s, re.I)
    if m:
        return re.sub(r"\s+", " ", m.group(1).upper().replace("'", ""))
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    return s[:32]


def months_between(a: date, b: date) -> float:
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.0


def window_end(origin: date, window_key: str) -> date:
    import calendar

    months = int(WINDOWS.get(window_key) or 12)
    y = origin.year + (origin.month - 1 + months) // 12
    m = (origin.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(origin.day, last))


def filter_series_in_window(
    series: list[dict[str, Any]],
    *,
    origin: date,
    end: date | None = None,
    include_baseline: bool = True,
) -> dict[str, Any]:
    """Return baseline (at/before origin) and post-origin points up to end."""
    from financial_intelligence.trends import normalize_series

    rows = normalize_series(series or [])
    baseline = None
    post: list[dict[str, Any]] = []
    for r in rows:
        pe = parse_period_to_date(r.get("period"))
        if pe is None:
            continue
        if pe <= origin:
            baseline = r
        elif end is None or pe <= end:
            post.append(r)
    if not include_baseline:
        baseline = None
    return {"baseline": baseline, "post": post, "n_post": len(post)}
