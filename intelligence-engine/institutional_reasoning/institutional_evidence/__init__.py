"""Phase 2 — Institutional Evidence Intelligence (soft-wire).

Converts point-in-time financial data into validated evidence packs
that frameworks consume. Frameworks never fetch.

Architecture v1.0.1 LOCKED — helper under institutional_reasoning.
Not a new top-level engine.
"""

from __future__ import annotations

from institutional_reasoning.institutional_evidence.production import (
    build_evidence_pack,
    package_for_governance,
    quality_gates,
)

__all__ = [
    "build_evidence_pack",
    "package_for_governance",
    "quality_gates",
]
