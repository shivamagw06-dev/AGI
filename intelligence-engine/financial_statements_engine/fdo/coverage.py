"""Coverage engine + company completeness checklist (FDO Phase 1)."""

from __future__ import annotations

from datetime import date
from typing import Any

from financial_statements_engine.fdo.calendar import (
    current_fy,
    fy_annual_period_end,
    fy_for_period_end,
    next_expected_filing,
    period_status,
    quarter_period_end,
    today_utc,
)
from financial_statements_engine.fdo.inventory import company_periods
from financial_statements_engine.fdo.schema import (
    ANNUAL_FRESHNESS_DAYS,
    PERIOD_MISSING,
    PERIOD_PRESENT,
    QUARTERLY_FRESHNESS_DAYS,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.schema import GOLD_UNIVERSE
from financial_statements_engine.util import now_iso


def _years_of_history(annuals: list[date]) -> int:
    if not annuals:
        return 0
    fys = {fy_for_period_end(pe) for pe in annuals}
    return len(fys)


def company_coverage(ticker: str, *, as_of: date | None = None) -> dict[str, Any]:
    d = as_of or today_utc()
    inv = company_periods(ticker)
    # Only count filings whose period has ended as of measurement date.
    annuals: list[date] = [pe for pe in inv["annual_period_ends"] if pe <= d]
    quarters: list[date] = [pe for pe in inv["quarterly_period_ends"] if pe <= d]
    latest_annual = annuals[-1] if annuals else None
    latest_quarter = quarters[-1] if quarters else None

    # Expected slots: last 5 annuals + last 8 quarters at or before as_of
    fy = current_fy(d)
    base_yy = int(fy.replace("FY", ""))
    expected_annuals = [fy_annual_period_end(f"FY{str(base_yy - i)[-2:]}") for i in range(5)]

    cursor_fy = base_yy
    cursor_q = 4
    for q in (4, 3, 2, 1):
        pe = quarter_period_end(fy, q)
        if pe <= d:
            cursor_q = q
            break
    else:
        cursor_fy = base_yy - 1
        cursor_q = 4

    expected_quarters: list[date] = []
    yy, qq = cursor_fy, cursor_q
    for _ in range(8):
        expected_quarters.append(quarter_period_end(f"FY{str(yy)[-2:]}", qq))
        qq -= 1
        if qq == 0:
            qq = 4
            yy -= 1

    have_a = set(annuals)
    have_q = set(quarters)
    missing_annual = [pe.isoformat() for pe in expected_annuals if pe not in have_a and pe <= d]
    missing_quarter = [pe.isoformat() for pe in expected_quarters if pe not in have_q and pe <= d]

    slots = len(expected_annuals) + len(expected_quarters)
    present = sum(1 for pe in expected_annuals if pe in have_a) + sum(1 for pe in expected_quarters if pe in have_q)
    coverage_pct = round(100.0 * present / slots, 2) if slots else 0.0

    stale_days = None
    if latest_quarter:
        stale_days = (d - latest_quarter).days
    elif latest_annual:
        stale_days = (d - latest_annual).days

    expected_next = next_expected_filing(latest_annual if latest_annual else None, quarters, as_of=d)

    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": inv["ticker"],
        "latest_annual": latest_annual.isoformat() if latest_annual else None,
        "latest_quarterly": latest_quarter.isoformat() if latest_quarter else None,
        "years_of_history": _years_of_history(annuals),
        "missing_periods": {"annual": missing_annual, "quarterly": missing_quarter},
        "expected_next_filing": expected_next,
        "coverage_pct": coverage_pct,
        "slots_present": present,
        "slots_expected": slots,
        "raw_evidence_n": inv["raw_evidence_n"],
        "stale_days": stale_days,
        "fresh_annual": bool(latest_annual and (d - latest_annual).days <= ANNUAL_FRESHNESS_DAYS),
        "fresh_quarterly": bool(latest_quarter and (d - latest_quarter).days <= QUARTERLY_FRESHNESS_DAYS),
        "as_of": d.isoformat(),
    }


def company_completeness(ticker: str, *, as_of: date | None = None) -> dict[str, Any]:
    """Human checklist: Annual FYxx / Q1–Q4 with status + overall completeness %."""
    d = as_of or today_utc()
    inv = company_periods(ticker)
    annuals = set(inv["annual_period_ends"])
    quarters = set(inv["quarterly_period_ends"])
    fy = current_fy(d)
    prior_yy = int(fy.replace("FY", "")) - 1
    prior_fy = f"FY{str(prior_yy)[-2:]}"

    checklist: list[dict[str, Any]] = []
    # Prior annual (e.g. Annual FY25 when current is FY26)
    annual_pe = fy_annual_period_end(prior_fy)
    checklist.append(
        {
            "label": f"Annual {prior_fy}",
            "period_end": annual_pe.isoformat(),
            "period_type": "annual",
            "status": period_status(period_end=annual_pe, have=annual_pe in annuals, as_of=d, period_type="annual"),
        }
    )
    # Current FY quarters
    for q in (1, 2, 3, 4):
        pe = quarter_period_end(fy, q)
        checklist.append(
            {
                "label": f"Q{q} {fy}",
                "period_end": pe.isoformat(),
                "period_type": "quarterly",
                "status": period_status(period_end=pe, have=pe in quarters, as_of=d, period_type="quarterly"),
            }
        )

    scored = [c for c in checklist if c["status"] != "not_released"]
    present_n = sum(1 for c in scored if c["status"] == PERIOD_PRESENT)
    completeness_pct = round(100.0 * present_n / len(scored), 2) if scored else 100.0

    cov = company_coverage(ticker, as_of=d)
    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": ticker.upper().strip(),
        "checklist": checklist,
        "overall_completeness_pct": completeness_pct,
        "missing": [c["label"] for c in checklist if c["status"] == PERIOD_MISSING],
        "expected": [c["label"] for c in checklist if c["status"] == "expected"],
        "coverage": cov,
        "as_of": d.isoformat(),
        "generated_at": now_iso(),
    }


def resolve_fdo_universe(universe: str | list[str] | None = None) -> list[str]:
    if isinstance(universe, list):
        return [str(t).upper().strip() for t in universe if str(t).strip()]
    name = (universe or "gold").lower().strip()
    if name in ("gold", "ic5", "default"):
        return list(GOLD_UNIVERSE)
    try:
        from financial_statements_engine.evidence_coverage.universe import resolve_universe

        return list(resolve_universe(name)["tickers"])
    except Exception:
        return list(GOLD_UNIVERSE)


def universe_coverage(universe: str | list[str] | None = "gold") -> dict[str, Any]:
    tickers = resolve_fdo_universe(universe)
    rows = [company_completeness(t) for t in tickers]
    avg_cov = round(sum(r["coverage"]["coverage_pct"] for r in rows) / len(rows), 2) if rows else 0.0
    avg_comp = round(sum(r["overall_completeness_pct"] for r in rows) / len(rows), 2) if rows else 0.0
    missing_latest = [r["ticker"] for r in rows if r["coverage"]["latest_annual"] is None]
    top_missing = sorted(rows, key=lambda r: r["overall_completeness_pct"])[:10]
    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "universe": universe if isinstance(universe, str) else "custom",
        "n": len(rows),
        "average_coverage_pct": avg_cov,
        "average_completeness_pct": avg_comp,
        "companies_missing_annual": missing_latest,
        "top_missing_companies": [
            {"ticker": r["ticker"], "completeness_pct": r["overall_completeness_pct"], "coverage_pct": r["coverage"]["coverage_pct"]}
            for r in top_missing
        ],
        "rows": rows,
        "as_of": now_iso(),
    }
