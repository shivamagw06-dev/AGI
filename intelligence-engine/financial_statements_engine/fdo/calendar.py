"""Indian fiscal-year helpers for coverage / completeness (FDO)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def parse_period_end(value: Any) -> date | None:
    if value is None:
        return None
    s = str(value).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def fy_for_period_end(pe: date) -> str:
    """India FY ending 31 Mar: 2025-03-31 → FY25; 2025-06-30 → FY26."""
    if pe.month >= 4:
        end_year = pe.year + 1
    else:
        end_year = pe.year
    return f"FY{str(end_year)[-2:]}"


def current_fy(as_of: date | None = None) -> str:
    d = as_of or today_utc()
    end_year = d.year + 1 if d.month >= 4 else d.year
    return f"FY{str(end_year)[-2:]}"


def fy_annual_period_end(fy_label: str) -> date:
    """FY25 → 2025-03-31."""
    yy = int(fy_label.replace("FY", "")[-2:])
    century = 2000 if yy < 70 else 1900
    return date(century + yy, 3, 31)


def quarter_period_end(fy_label: str, quarter: int) -> date:
    """Q1–Q4 of FY ending March. Q1=Jun, Q2=Sep, Q3=Dec, Q4=Mar."""
    annual = fy_annual_period_end(fy_label)
    mapping = {1: (annual.year - 1, 6, 30), 2: (annual.year - 1, 9, 30), 3: (annual.year - 1, 12, 31), 4: (annual.year, 3, 31)}
    y, m, d = mapping[quarter]
    return date(y, m, d)


def expected_release_lag_days(period_type: str) -> int:
    return 60 if period_type == "annual" else 45


def quarter_start(period_end: date) -> date:
    """Start of the India FY quarter that ends on period_end."""
    # Q ends Jun/Sep/Dec/Mar → starts Apr/Jul/Oct/Jan
    mapping = {6: (period_end.year, 4, 1), 9: (period_end.year, 7, 1), 12: (period_end.year, 10, 1), 3: (period_end.year, 1, 1)}
    y, m, day = mapping.get(period_end.month, (period_end.year, period_end.month, 1))
    return date(y, m, day)


def period_status(
    *,
    period_end: date,
    have: bool,
    as_of: date | None = None,
    period_type: str = "quarterly",
) -> str:
    """present | missing | expected | not_released."""
    from datetime import timedelta

    from financial_statements_engine.fdo.schema import (
        PERIOD_EXPECTED,
        PERIOD_MISSING,
        PERIOD_NOT_RELEASED,
        PERIOD_PRESENT,
    )

    if have:
        return PERIOD_PRESENT
    d = as_of or today_utc()
    lag = expected_release_lag_days(period_type)

    # Future periods that have not started → not released.
    # Current in-progress period → expected (awaiting release after close).
    if period_end > d:
        if period_type == "quarterly" and quarter_start(period_end) <= d:
            return PERIOD_EXPECTED
        if period_type == "annual":
            # Annual expected during the FY it covers once prior year closed.
            fy_start = date(period_end.year - 1, 4, 1)
            if fy_start <= d:
                return PERIOD_EXPECTED
        return PERIOD_NOT_RELEASED

    if d <= period_end + timedelta(days=lag):
        return PERIOD_EXPECTED
    return PERIOD_MISSING


def next_expected_filing(have_annual: date | None, have_quarters: list[date], as_of: date | None = None) -> dict[str, Any]:
    d = as_of or today_utc()
    fy = current_fy(d)
    # Prefer next missing quarter in current FY, else next annual
    for q in (1, 2, 3, 4):
        pe = quarter_period_end(fy, q)
        if pe > d:
            return {"filing_type": "quarterly", "label": f"Q{q} {fy}", "period_end": pe.isoformat(), "status": "not_released"}
        if pe not in have_quarters:
            st = period_status(period_end=pe, have=False, as_of=d, period_type="quarterly")
            return {"filing_type": "quarterly", "label": f"Q{q} {fy}", "period_end": pe.isoformat(), "status": st}
    annual_pe = fy_annual_period_end(fy)
    if have_annual != annual_pe:
        st = period_status(period_end=annual_pe, have=False, as_of=d, period_type="annual")
        return {"filing_type": "annual", "label": f"Annual {fy}", "period_end": annual_pe.isoformat(), "status": st}
    # roll to next FY Q1
    next_fy_year = int(fy.replace("FY", "")) + 1
    next_fy = f"FY{next_fy_year:02d}"[-4:] if False else f"FY{str(next_fy_year)[-2:]}"
    pe = quarter_period_end(next_fy, 1)
    return {"filing_type": "quarterly", "label": f"Q1 {next_fy}", "period_end": pe.isoformat(), "status": "not_released"}
