"""Phase 3 — Institutional Knowledge Intelligence (IKI).

Transform stored frameworks into executable institutional judgement.
Soft-wire under institutional_reasoning. Not a new top-level engine.
Architecture v1.0.1 LOCKED — no Neo4j required.
"""

from __future__ import annotations

from institutional_reasoning.iki.production import (
    dashboard,
    package_for_governance,
    plan,
    quality_gates,
    run_judgement_suite,
)

__all__ = [
    "dashboard",
    "package_for_governance",
    "plan",
    "quality_gates",
    "run_judgement_suite",
]
