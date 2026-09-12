"""KRIG freshness facade — delegates to Knowledge Freshness Engine (KFE)."""

from __future__ import annotations

from app.kfe.engine import (
    OBJECT_TYPE_SLA,
    SLA_BY_SECTION,
    FreshnessEngine,
    FreshnessSla,
    KnowledgeFreshnessEngine,
    current_as_of_statement,
    evaluate_freshness,
    evaluate_object_freshness,
    format_age,
)

__all__ = [
    "FreshnessSla",
    "SLA_BY_SECTION",
    "OBJECT_TYPE_SLA",
    "evaluate_freshness",
    "evaluate_object_freshness",
    "format_age",
    "current_as_of_statement",
    "FreshnessEngine",
    "KnowledgeFreshnessEngine",
]
