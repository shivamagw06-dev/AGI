"""Institutional Decision Engine V2 — final constitutional orchestrator."""

from decision_engine_v2.production import (
    analyse,
    audit,
    company,
    dashboard,
    freeze_review,
    health,
    monitoring,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from decision_engine_v2.schema import ARCHITECTURE_FROZEN, IDEV2_VERSION, PRIMARY_QUESTION

__all__ = [
    "ARCHITECTURE_FROZEN",
    "IDEV2_VERSION",
    "PRIMARY_QUESTION",
    "analyse",
    "audit",
    "company",
    "dashboard",
    "freeze_review",
    "health",
    "monitoring",
    "quality_gates",
    "soft_slice_for_analyst",
    "soft_slice_for_irs",
]
