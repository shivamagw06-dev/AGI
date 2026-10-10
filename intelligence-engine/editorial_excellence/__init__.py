"""Editorial Excellence Program v1.0 — continuous writing improvement."""

from editorial_excellence.production import (
    apply_editorial_excellence,
    health,
    run_monthly_report,
    run_weekly_review,
)
from editorial_excellence.rules import EDITORIAL_RULES, list_rules, rule_count
from editorial_excellence.schema import PROGRAM_VERSION
from editorial_excellence.scorecard import quality_gates, score_editorial
from editorial_excellence.workspace import build_review_workspace

__all__ = [
    "EDITORIAL_RULES",
    "PROGRAM_VERSION",
    "apply_editorial_excellence",
    "build_review_workspace",
    "health",
    "list_rules",
    "quality_gates",
    "rule_count",
    "run_monthly_report",
    "run_weekly_review",
    "score_editorial",
]
