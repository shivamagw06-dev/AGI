"""Recommendation drift — reason codes, budgets, review policy."""

from __future__ import annotations

from typing import Any

DRIFT_VERSION = "recommendation-drift-v1.0.0"
PROGRAMME = "AGIB_RECOMMENDATION_DRIFT"

# Every recommendation change must carry one of these reason codes.
REASON_CODES: dict[str, str] = {
    "DATA": "New evidence (earnings, shareholding, filing)",
    "MARKET": "Live price or valuation changed",
    "MODEL": "Decision Engine or scoring logic changed",
    "GOVERNANCE": "Gate/readiness rule changed",
    "BUGFIX": "Previous implementation error corrected",
    "UNKNOWN": "No explainable reason — investigate as regression",
    "NONE": "No recommendation change",
}

# UNKNOWN is a regression until explained
UNKNOWN_IS_REGRESSION = True

# Magnitude fields compared across releases
MAGNITUDE_FIELDS: tuple[str, ...] = (
    "company_quality",
    "financial_quality",
    "valuation",
    "macro",
    "technical",
    "risk",
    "recommendation_readiness",
    "overall_score",
)

# Drift budget — anything outside fails the release
DRIFT_BUDGET: dict[str, Any] = {
    "recommendation_change_pct_max": 5.0,
    "unknown_drift_pct_max": 0.0,
    "governance_failures_max": 0,
    "runtime_regression_pct_max": 10.0,
    "average_readiness_change_pct_max": 2.0,
    # Absolute swing on 0–10 scores that forces human review
    "large_valuation_swing": 1.0,
    "large_quality_swing": 1.5,
}

# Human review triggers
REVIEW_TRIGGERS = (
    "UNKNOWN",
    "GOVERNANCE",
    "large_valuation_swing",
    "budget_breach",
)
