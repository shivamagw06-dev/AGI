"""Finance Academy Production Integration (FAPI) v1.0.

Additive integration capability — NOT a new engine.
Wires the existing Finance Academy into production reasoning paths.
"""

from academy.fapi.production import (
    FAPI_VERSION,
    is_production_enabled,
    package_for_query,
    attach_for_engine,
    apply_ve_assumptions,
    enrich_reasoning,
    production_dashboard,
    run_ab_probe,
    quality_gates,
    record_engine_consumption,
)

__all__ = [
    "FAPI_VERSION",
    "is_production_enabled",
    "package_for_query",
    "attach_for_engine",
    "apply_ve_assumptions",
    "enrich_reasoning",
    "production_dashboard",
    "run_ab_probe",
    "quality_gates",
    "record_engine_consumption",
]
