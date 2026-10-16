"""Sector Intelligence Framework (SIF) v1.0.

Additive institutional analysis framework — NOT a new engine, NOT a curriculum.
Teaches when/where/how to apply Finance Academy concepts by sector.
"""

from sif.production import (
    SIF_VERSION,
    is_sif_enabled,
    analyse_query,
    attach_for_engine,
    valuation_guidance,
    quality_gates,
    production_dashboard,
)

__all__ = [
    "SIF_VERSION",
    "is_sif_enabled",
    "analyse_query",
    "attach_for_engine",
    "valuation_guidance",
    "quality_gates",
    "production_dashboard",
]
