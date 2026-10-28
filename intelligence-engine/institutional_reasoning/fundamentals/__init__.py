"""Institutional Fundamentals — primitives in, derived metrics out.

Ratios (PE, PB, EV/EBITDA, ROIC, ROE, margins, FCF, debt) are never stored.
They are computed from primitive series with a recorded formula and inputs so
every number is reproducible and auditable.

Soft-wire under institutional_reasoning. Architecture v1.0.1 LOCKED.
"""

from institutional_reasoning.fundamentals.production import (
    available_metrics,
    derive_latest,
    derive_series,
    has_primitives,
    health,
    quality_gates,
    verify_derivation,
)
from institutional_reasoning.fundamentals.risk_derivations import (
    derive_risk_metrics,
    risk_field_payload,
)
from institutional_reasoning.fundamentals.universe import (
    coverage_for,
    tier_report,
    universe_health,
)

__all__ = [
    "available_metrics",
    "coverage_for",
    "derive_latest",
    "derive_risk_metrics",
    "derive_series",
    "has_primitives",
    "health",
    "quality_gates",
    "risk_field_payload",
    "tier_report",
    "universe_health",
    "verify_derivation",
]
