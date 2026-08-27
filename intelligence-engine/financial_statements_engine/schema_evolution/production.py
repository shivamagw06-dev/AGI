"""Schema Evolution production façades."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.schema_evolution.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.schema_evolution.service import get_service, resolve_label
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    svc = get_service()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "mapping_count": len(svc.list_mappings()),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_04_PARSING_NORMALIZATION_ENGINE.md#25-schema-evolution-engine-architect-recommendation",
        "as_of": now_iso(),
    }


def resolve_payload(
    label: str,
    *,
    as_of: str | None = None,
    reporting_standard: str | None = "IND_AS",
    taxonomy: str | None = None,
) -> dict[str, Any]:
    result = resolve_label(label, as_of=as_of, reporting_standard=reporting_standard, taxonomy=taxonomy)
    result.update(
        {
            "workstream_id": WORKSTREAM_ID,
            "issues_recommendations": False,
            "as_of": now_iso(),
        }
    )
    return result
