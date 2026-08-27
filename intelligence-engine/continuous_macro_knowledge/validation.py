"""Validate raw macro releases before normalization."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.schema import CATEGORIES, RawMacroRelease


def validate_release(raw: RawMacroRelease) -> dict[str, Any]:
    failures: list[str] = []
    if not raw.source:
        failures.append("missing_source")
    if not raw.country:
        failures.append("missing_country")
    if not raw.indicator:
        failures.append("missing_indicator")
    if not raw.release_date:
        failures.append("missing_release_date")
    if raw.category not in CATEGORIES:
        failures.append("invalid_category")
    # Numeric indicators should have a value unless document-type
    doc_like = raw.indicator.lower() in {"mpc statement", "union budget"} or raw.current_value is None
    if not doc_like and raw.current_value is None:
        failures.append("missing_current_value")
    if raw.importance not in {"Critical", "High", "Medium", "Low"}:
        failures.append("invalid_importance")

    ok = not failures
    return {
        "ok": ok,
        "failures": failures,
        "release_id": raw.release_id,
        "indicator": raw.indicator,
        "source": raw.source,
    }
