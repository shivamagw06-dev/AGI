"""Phase 6 — Institutional Outcome Intelligence (IOI).

Soft-wire under institutional_reasoning. Measures every portfolio decision
against reality. Links DJG → PDG → Market Outcome → Attribution → Review.

NO learning. Prerequisite for Phase 7 Continuous Adaptive Learning.
Architecture v1.0.1 LOCKED.
"""

from institutional_reasoning.ioi.production import (
    dashboard,
    evaluate_decision,
    quality_gates,
    run_outcome_suite,
    track_decision,
)

__all__ = [
    "dashboard",
    "evaluate_decision",
    "quality_gates",
    "run_outcome_suite",
    "track_decision",
]
