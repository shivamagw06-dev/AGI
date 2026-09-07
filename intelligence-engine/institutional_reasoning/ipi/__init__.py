"""Phase 5 — Institutional Portfolio Intelligence (IPI).

Soft-wire under institutional_reasoning. Transforms research packages into
evidence-backed, policy-governed portfolio decisions with a Portfolio Decision
Graph (PDG) linked to research DJGs.

Architecture v1.0.1 LOCKED — no new top-level engine, no DJG replacement.
"""

from institutional_reasoning.ipi.production import (
    dashboard,
    decide_portfolio,
    package_for_governance,
    quality_gates,
    run_portfolio_suite,
)

__all__ = [
    "dashboard",
    "decide_portfolio",
    "package_for_governance",
    "quality_gates",
    "run_portfolio_suite",
]
