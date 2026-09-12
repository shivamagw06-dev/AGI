"""Academy Certification Suite (ACS) V1 — institutional intelligence certification."""

from academy.certification.production import (
    certify,
    dashboard,
    is_enabled,
    list_inventory,
    quality_gates,
    run_one,
)
from academy.certification.schema import ACS_VERSION

__all__ = [
    "ACS_VERSION",
    "certify",
    "dashboard",
    "is_enabled",
    "list_inventory",
    "quality_gates",
    "run_one",
]
