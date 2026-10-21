"""Validate historical observations before normalization."""

from __future__ import annotations

from typing import Any

from historical_macro_intelligence.schema import SOURCES, RawHistoricalObservation

_VALID_CATEGORIES = {
    "Monetary",
    "Inflation",
    "Growth",
    "Fiscal",
    "External Sector",
    "Financial Markets",
}


def validate_observation(raw: RawHistoricalObservation) -> dict[str, Any]:
    failures: list[str] = []
    if raw.source not in SOURCES:
        failures.append("unknown_source")
    if not raw.country:
        failures.append("missing_country")
    if not raw.indicator:
        failures.append("missing_indicator")
    if not raw.period:
        failures.append("missing_period")
    if not raw.publication_date:
        failures.append("missing_publication_date")
    if raw.category not in _VALID_CATEGORIES:
        failures.append("invalid_category")
    doc_like = raw.value is None
    if not doc_like and raw.value is None:
        failures.append("missing_value")
    return {
        "ok": not failures,
        "failures": failures,
        "observation_id": raw.observation_id,
        "indicator": raw.indicator,
        "period": raw.period,
    }
