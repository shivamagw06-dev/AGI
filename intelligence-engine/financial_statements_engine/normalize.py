"""Normalization Layer — terminology, units, periods. No calculations."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.registry import resolve, to_value_inr


def normalize_fields(
    fields: dict[str, Any],
    *,
    default_unit_scale: str = "crores",
    currency: str = "INR",
) -> dict[str, Any]:
    """Map extractor fields → canonical metrics with value_inr.

    Unknown names go to ``unmapped``; never invent canonical names.
    """
    metrics: dict[str, Any] = {}
    unmapped: dict[str, Any] = {}

    for raw_name, payload in (fields or {}).items():
        if isinstance(payload, dict):
            reported = payload.get("value")
            unit_scale = payload.get("unit_scale") or payload.get("unit") or default_unit_scale
            # strip currency-ish unit tokens
            if isinstance(unit_scale, str) and unit_scale.upper().startswith("INR"):
                # e.g. INR_Crores
                tail = unit_scale.split("_")[-1].lower() if "_" in unit_scale else default_unit_scale
                unit_scale = tail if tail in ("ones", "thousands", "lakhs", "crores", "millions", "billions") else default_unit_scale
            extra = {k: v for k, v in payload.items() if k not in ("value", "unit", "unit_scale")}
        else:
            reported = payload
            unit_scale = default_unit_scale
            extra = {}

        canon = resolve(str(raw_name))
        if not canon:
            unmapped[str(raw_name)] = payload
            continue

        metrics[canon] = {
            "reported_value": reported,
            "unit_scale": unit_scale,
            "value_inr": to_value_inr(reported if isinstance(reported, (int, float)) else None, str(unit_scale)),
            "currency": currency,
            "source_field": raw_name,
            **extra,
        }

    return {
        "metrics": metrics,
        "unmapped": unmapped,
        "currency": currency,
        "layer": "normalization",
    }
