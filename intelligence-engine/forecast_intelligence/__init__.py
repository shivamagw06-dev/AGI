"""Forecast Intelligence Engine (FIE) V1 — what future paths are plausible?"""

from forecast_intelligence.production import (
    analyse,
    catalysts,
    company,
    dashboard,
    health,
    quality_gates,
    scenarios,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from forecast_intelligence.schema import FIE_VERSION, PRIMARY_QUESTION

__all__ = [
    "FIE_VERSION",
    "PRIMARY_QUESTION",
    "analyse",
    "catalysts",
    "company",
    "dashboard",
    "health",
    "quality_gates",
    "scenarios",
    "soft_slice_for_analyst",
    "soft_slice_for_irs",
]
