"""Normalization stage — Metric Registry + Schema Evolution only (no parser-local maps)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.metric_registry.service import get_metric
from financial_statements_engine.parsing.schema import CONFIDENCE_FLAG_THRESHOLD
from financial_statements_engine.schema_evolution.service import resolve_label


def map_metrics(
    fields: dict[str, Any],
    *,
    as_of: str | None = None,
    reporting_standard: str = "IND_AS",
    extraction_confidence: float = 0.0,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    unknown: dict[str, Any] = {}
    collisions: dict[str, list[str]] = {}

    for raw_name, payload in (fields or {}).items():
        resolved = resolve_label(
            str(raw_name),
            as_of=as_of,
            reporting_standard=reporting_standard,
        )
        canon = resolved.get("canonical")
        if not canon:
            unknown[str(raw_name)] = payload
            continue

        row = dict(payload) if isinstance(payload, dict) else {"value": payload, "reported_value": payload}
        # Preserve explicit nulls — never coerce missing to 0
        if "value" in row and "reported_value" not in row:
            row["reported_value"] = row.get("value")
        if row.get("reported_value") is None and row.get("value") is None:
            row["reported_value"] = None
            row["normalized_value"] = None

        norm_conf = 1.0 if resolved.get("via") else 0.0
        overall = min(1.0, 0.5 * float(extraction_confidence) + 0.5 * norm_conf)
        row.update(
            {
                "source_field": raw_name,
                "normalization_via": resolved.get("via"),
                "extraction_confidence": extraction_confidence,
                "normalization_confidence": norm_conf,
                "overall_confidence": overall,
                "confidence_flagged": overall < CONFIDENCE_FLAG_THRESHOLD,
                "metric_record": get_metric(canon),
            }
        )

        if canon in metrics:
            collisions.setdefault(canon, []).append(str(raw_name))
            prev = metrics[canon]
            prev_sources = list(prev.get("duplicate_sources") or [prev.get("source_field")])
            prev_sources.append(str(raw_name))
            row["duplicate_sources"] = prev_sources
            # Keep first mapped value; flag duplicate (do not invent merge)
        metrics[canon] = row

    return {
        "metrics": metrics,
        "unknown_fields": unknown,
        "collisions": collisions,
        "layer": "metric_mapping",
        "uses_parser_local_synonyms": False,
    }
