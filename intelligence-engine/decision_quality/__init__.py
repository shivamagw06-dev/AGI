"""Institutional Decision Quality (IDQ) — observability layer (Sprint 7).

Measures how good AGIB decisions are. Never reasons.
Phases 1–7 and Knowledge Factory remain frozen.
"""

from __future__ import annotations

from decision_quality.dashboard import decision_quality_dashboard
from decision_quality.pipeline import run_decision_quality_pipeline
from decision_quality.production import health, quality_gates
from decision_quality.schema import HALL_CATEGORIES, IDQ_VERSION

__all__ = [
    "HALL_CATEGORIES",
    "IDQ_VERSION",
    "decision_quality_dashboard",
    "health",
    "quality_gates",
    "run_decision_quality_pipeline",
]
