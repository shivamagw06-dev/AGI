"""Evidence Intelligence Layer V1 — sources, peers/history gaps, explainable confidence."""

from academy.evidence.production import (
    case_pack,
    dashboard,
    explain_confidence,
    is_enabled,
    quality_gates,
    soft_slice_for_irs,
    support,
)
from academy.evidence.schema import EIL_VERSION

__all__ = [
    "EIL_VERSION",
    "case_pack",
    "dashboard",
    "explain_confidence",
    "is_enabled",
    "quality_gates",
    "soft_slice_for_irs",
    "support",
]
