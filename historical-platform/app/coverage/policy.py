"""Historical coverage policy — measurable completeness targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.contracts.models import CoverageStatus


@dataclass(frozen=True)
class CoverageTarget:
    category: str
    description: str
    expected_key: str  # settings / heuristic key
    default_expected: int


COVERAGE_TARGETS: tuple[CoverageTarget, ...] = (
    CoverageTarget(
        "daily_ohlcv",
        "Maximum available daily OHLCV from Yahoo Finance",
        "min_daily_bars",
        2500,
    ),
    CoverageTarget(
        "quarterly_financials",
        "Maximum available quarterly financial statements",
        "min_quarterly_financials",
        20,
    ),
    CoverageTarget(
        "annual_financials",
        "Maximum available annual financial statements",
        "min_annual_financials",
        10,
    ),
    CoverageTarget(
        "balance_sheets",
        "Maximum available balance sheet history",
        "min_quarterly_financials",
        20,
    ),
    CoverageTarget(
        "cash_flows",
        "Maximum available cash-flow history",
        "min_quarterly_financials",
        20,
    ),
    CoverageTarget(
        "dividends",
        "Full available dividend history",
        "min_dividends",
        5,
    ),
    CoverageTarget(
        "corporate_actions",
        "Full available corporate action history",
        "min_actions",
        1,
    ),
    CoverageTarget(
        "corporate_events",
        "All available corporate announcements / events",
        "min_events",
        5,
    ),
    CoverageTarget(
        "company_ir_reports",
        "Every available IR report (annual/quarterly/presentation/transcript)",
        "min_ir_reports",
        4,
    ),
    CoverageTarget(
        "company_profile_history",
        "Versioned historical company information",
        "min_profiles",
        1,
    ),
    CoverageTarget(
        "news_metadata",
        "Maximum available historical news metadata",
        "min_news",
        10,
    ),
)


def score_completeness(present: int, expected: int) -> dict[str, Any]:
    expected = max(1, int(expected))
    present = max(0, int(present))
    ratio = min(1.0, present / expected)
    if present == 0:
        status = CoverageStatus.MISSING
    elif ratio >= 0.95:
        status = CoverageStatus.COMPLETE
    elif ratio >= 0.5:
        status = CoverageStatus.PARTIAL
    else:
        status = CoverageStatus.SPARSE
    return {
        "present": present,
        "expected": expected,
        "completeness": round(ratio, 4),
        "status": status.value,
    }


def expected_for(category: str, settings: Any | None = None) -> int:
    for t in COVERAGE_TARGETS:
        if t.category == category:
            if settings is not None and hasattr(settings, t.expected_key):
                return int(getattr(settings, t.expected_key))
            # optional attributes with defaults
            defaults = {
                "min_dividends": 5,
                "min_actions": 1,
                "min_events": 5,
                "min_ir_reports": 4,
                "min_profiles": 1,
                "min_news": 10,
            }
            if settings is not None and t.expected_key in defaults:
                return int(getattr(settings, t.expected_key, defaults[t.expected_key]))
            return t.default_expected
    return 1


def policy_snapshot(settings: Any | None = None) -> dict[str, Any]:
    return {
        "policy": "historical_coverage_v1",
        "targets": [
            {
                "category": t.category,
                "description": t.description,
                "expected": expected_for(t.category, settings),
            }
            for t in COVERAGE_TARGETS
        ],
    }
