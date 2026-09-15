"""Gap scheduler — prioritise largest evidence gaps first (FDO Phase 1)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.fdo.coverage import company_coverage, company_completeness, resolve_fdo_universe
from financial_statements_engine.fdo.schema import (
    WEIGHT_HIGH_PRIORITY_TICKER,
    WEIGHT_LOW_COVERAGE,
    WEIGHT_MISSING_LATEST_ANNUAL,
    WEIGHT_MISSING_LATEST_QUARTER,
    WEIGHT_STALE_DAYS,
    WEIGHT_ZERO_RAW_EVIDENCE,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.schema import GOLD_UNIVERSE
from financial_statements_engine.util import now_iso


def gap_priority_score(ticker: str, *, high_priority: set[str] | None = None) -> dict[str, Any]:
    """Higher score = schedule sooner (largest Raw Evidence gaps first)."""
    cov = company_coverage(ticker)
    comp = company_completeness(ticker)
    score = 0.0
    reasons: list[str] = []

    raw_n = int(cov.get("raw_evidence_n") or 0)
    if raw_n <= 0:
        score += WEIGHT_ZERO_RAW_EVIDENCE
        reasons.append("zero_raw_evidence")

    if not cov.get("latest_annual"):
        score += WEIGHT_MISSING_LATEST_ANNUAL
        reasons.append("missing_latest_annual")
    if not cov.get("latest_quarterly"):
        score += WEIGHT_MISSING_LATEST_QUARTER
        reasons.append("missing_latest_quarterly")

    # Low coverage → higher urgency
    cov_pct = float(cov.get("coverage_pct") or 0.0)
    score += WEIGHT_LOW_COVERAGE * (1.0 - cov_pct / 100.0)
    if cov_pct < 50:
        reasons.append("low_coverage")

    stale = cov.get("stale_days")
    if isinstance(stale, int) and stale > 90:
        score += min(50.0, WEIGHT_STALE_DAYS * (stale - 90))
        reasons.append("stale_company")

    missing_n = len(comp.get("missing") or [])
    score += 5.0 * missing_n
    if missing_n:
        reasons.append(f"missing_slots:{missing_n}")

    hp = high_priority or set(GOLD_UNIVERSE)
    if ticker.upper() in hp:
        score += WEIGHT_HIGH_PRIORITY_TICKER
        reasons.append("high_priority_universe")

    # Recently released / expected filings bump
    nxt = cov.get("expected_next_filing") or {}
    if nxt.get("status") == "expected":
        score += 15.0
        reasons.append("expected_filing_window")
    if nxt.get("status") == "missing":
        score += 20.0
        reasons.append("overdue_expected_filing")

    return {
        "ticker": ticker.upper().strip(),
        "score": round(score, 2),
        "reasons": reasons,
        "coverage_pct": cov_pct,
        "completeness_pct": comp.get("overall_completeness_pct"),
        "raw_evidence_n": raw_n,
        "latest_annual": cov.get("latest_annual"),
        "latest_quarterly": cov.get("latest_quarterly"),
        "expected_next_filing": nxt,
        "missing": comp.get("missing"),
    }


def plan_gap_schedule(
    universe: str | list[str] | None = "gold",
    *,
    limit: int = 50,
) -> dict[str, Any]:
    tickers = resolve_fdo_universe(universe)
    ranked = [gap_priority_score(t) for t in tickers]
    ranked.sort(key=lambda r: (-float(r["score"]), r["ticker"]))
    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "universe": universe if isinstance(universe, str) else "custom",
        "policy": "largest_evidence_gaps_first",
        "n": len(ranked[:limit]),
        "queue": ranked[:limit],
        "as_of": now_iso(),
    }
