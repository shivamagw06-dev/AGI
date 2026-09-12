"""CFDM production façades (FSE-03)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.cfdm.schema import (
    CANONICAL_OBJECTS,
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.metric_registry.production import health as metric_registry_health
from financial_statements_engine.metric_registry.schema import REGISTRY_VERSION
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    reg = metric_registry_health()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "canonical_objects": list(CANONICAL_OBJECTS),
        "metric_registry_version": REGISTRY_VERSION,
        "metric_registry": reg.get("manifest"),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "consumer_may_define_schema": False,
        "spec": "docs/FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md",
        "as_of": now_iso(),
    }
