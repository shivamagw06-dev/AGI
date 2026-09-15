"""Valuation Policy & Applicability Engine (VPAE) — Phase 8.2A.

Mandatory decision layer in front of the Unified Valuation Engine. Extends
``valuation_terminal.sector_lens`` with instrument type, profitability,
coverage and DQIV. Does not compute multiples.
"""

from valuation_policy.engine import applicable_metrics, evaluate, is_meaningful
from valuation_policy.production import (
    applicability,
    coverage,
    explanation,
    health,
    model,
    status,
    universe,
)
from valuation_policy.models import ENGINE_CODE, VERSION

__all__ = [
    "ENGINE_CODE",
    "VERSION",
    "evaluate",
    "is_meaningful",
    "applicable_metrics",
    "health",
    "applicability",
    "model",
    "explanation",
    "coverage",
    "status",
    "universe",
]
