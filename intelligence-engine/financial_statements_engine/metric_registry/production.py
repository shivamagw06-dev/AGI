"""Metric Registry production façades (FSE-03)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.metric_registry.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REGISTRY_VERSION,
    SUBSYSTEM,
    WORKSTREAM_ID,
)
from financial_statements_engine.metric_registry.service import (
    get_metric,
    list_metrics,
    manifest,
    resolve,
)
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "registry_version": REGISTRY_VERSION,
        "manifest": manifest(),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md",
        "as_of": now_iso(),
    }


def resolve_payload(name: str) -> dict[str, Any]:
    canon = resolve(name)
    return {
        "ok": canon is not None,
        "input": name,
        "canonical": canon,
        "metric": get_metric(canon) if canon else None,
        "registry_version": REGISTRY_VERSION,
        "workstream_id": WORKSTREAM_ID,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def metrics_payload(*, category: str | None = None, appendix_only: bool = False) -> dict[str, Any]:
    rows = list_metrics(category=category, appendix_only=appendix_only)
    return {
        "ok": True,
        "registry_version": REGISTRY_VERSION,
        "workstream_id": WORKSTREAM_ID,
        "n": len(rows),
        "metrics": rows,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }
