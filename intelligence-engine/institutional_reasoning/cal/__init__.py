"""Phase 7 — Continuous Adaptive Learning (CAL).

Soft-wire under institutional_reasoning. Learning Governance Layer between
Outcome Intelligence and Production.

Never rewrite rules automatically.
Proposal → Validation → Simulation → Approval → Version.

Architecture v1.0.1 LOCKED.
"""

from institutional_reasoning.cal.production import (
    dashboard,
    govern_learning,
    propose_from_outcome,
    quality_gates,
    run_learning_suite,
)

__all__ = [
    "dashboard",
    "govern_learning",
    "propose_from_outcome",
    "quality_gates",
    "run_learning_suite",
]
