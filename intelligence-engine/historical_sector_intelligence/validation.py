"""Validate historical sector observations."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SECTOR_UNIVERSE
from historical_sector_intelligence.schema import RawHistoricalSectorObservation


def validate_observation(raw: RawHistoricalSectorObservation) -> dict[str, Any]:
    errors: list[str] = []
    if raw.sector_key not in SECTOR_UNIVERSE:
        errors.append("unknown_sector")
    if not raw.period:
        errors.append("period_required")
    if not raw.indicator:
        errors.append("indicator_required")
    if not raw.category:
        errors.append("category_required")
    if not raw.source:
        errors.append("source_required")
    if raw.source in {"yahoo", "nse_live", "external_api"}:
        errors.append("external_live_source_forbidden")
    return {"ok": not errors, "errors": errors, "sector": raw.sector_key, "period": raw.period}
