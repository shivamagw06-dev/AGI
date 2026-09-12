"""Phase 4 — Institutional Research Orchestration (IRO).

Coordinate an entire institutional research workflow from a single
investment objective. Each research task produces its own Decision
Justification Graph; the investment committee merges them.

Soft-wire under institutional_reasoning. Not a new top-level engine.
Architecture v1.0.1 LOCKED.
"""

from __future__ import annotations

from institutional_reasoning.iro.production import (
    dashboard,
    quality_gates,
    run_assignment,
    run_planning_suite,
)

__all__ = [
    "dashboard",
    "quality_gates",
    "run_assignment",
    "run_planning_suite",
]
