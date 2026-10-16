"""DQIV validation for historical valuation observations."""

from __future__ import annotations

from typing import Any, Optional

from historical_valuation_intelligence.models import EXTREME_EV, EXTREME_PB, EXTREME_PE


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return None if out != out else out
    except (TypeError, ValueError):
        return None


def validate_observation(row: dict[str, Any], *, today: Optional[str] = None) -> dict[str, Any]:
    """Validate one historical observation. Warnings are not errors."""
    errors: list[str] = []
    warnings: list[str] = []

    date = str(row.get("date") or row.get("period") or "")
    if not date:
        errors.append("missing_date")
    if today and date and date > today:
        errors.append("future_price_date")

    pe = _num(row.get("pe"))
    pb = _num(row.get("pb"))
    ev_ebitda = _num(row.get("ev_ebitda"))
    ev_sales = _num(row.get("ev_sales"))
    eps = _num(row.get("ttm_eps") or row.get("eps"))
    book = _num(row.get("book_value_per_share"))
    ebitda = _num(row.get("ttm_ebitda") or row.get("ebitda"))

    if pe is not None and pe <= 0:
        errors.append("non_positive_pe")
    if pe is not None and pe > EXTREME_PE:
        warnings.append(f"extreme_pe:{pe}")
    if pb is not None and pb <= 0:
        errors.append("non_positive_pb")
    if pb is not None and pb > EXTREME_PB:
        warnings.append(f"extreme_pb:{pb}")
    if book is not None and book < 0:
        warnings.append("negative_book_value")
    if eps is not None and eps <= 0 and pe is not None:
        errors.append("pe_with_non_positive_eps")
    if ebitda is not None and ebitda <= 0 and ev_ebitda is not None:
        errors.append("ev_ebitda_with_non_positive_ebitda")
    if ev_ebitda is not None and ev_ebitda > EXTREME_EV:
        warnings.append(f"extreme_ev_ebitda:{ev_ebitda}")
    if ev_sales is not None and ev_sales < 0:
        errors.append("negative_ev_sales")

    mcap = _num(row.get("market_cap"))
    ev = _num(row.get("enterprise_value"))
    if mcap is not None and mcap < 0:
        errors.append("negative_market_cap")
    if ev is not None and mcap is not None and ev < 0 and abs(ev) > abs(mcap) * 2:
        warnings.append("implausible_enterprise_value")

    status = "ok" if not errors else "fail"
    if status == "ok" and warnings:
        status = "warn"
    return {
        "ok": not errors,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def validate_series(points: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    """Series-level checks: duplicates, chronology, impossible values."""
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    prev = None
    bad = 0
    for p in points:
        period = str(p.get("period") or p.get("date") or "")
        if period in seen:
            errors.append(f"duplicate_observation:{period}")
        seen.add(period)
        if prev and period < prev:
            errors.append("out_of_order")
        prev = period
        value = _num(p.get("value"))
        if value is None:
            continue
        if metric == "pe" and (value <= 0 or value > EXTREME_PE):
            bad += 1
            if value <= 0:
                errors.append(f"invalid_pe:{period}")
            else:
                warnings.append(f"extreme_pe:{period}:{value}")
        if metric == "pb" and value <= 0:
            errors.append(f"invalid_pb:{period}")
    return {
        "ok": not errors,
        "status": "ok" if not errors else "fail",
        "errors": errors[:20],
        "warnings": warnings[:20],
        "extreme_count": bad,
        "observation_count": len(points),
    }
