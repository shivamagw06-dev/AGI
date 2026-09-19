"""Validate historical market observations."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MARKET_UNIVERSE
from historical_market_intelligence.schema import RawHistoricalMarketObservation

FORBIDDEN_LIVE_SOURCES = {"yahoo", "groww", "nse_live", "external_api", "yfinance"}


def validate_observation(raw: RawHistoricalMarketObservation) -> dict[str, Any]:
    errors: list[str] = []
    if raw.market_key not in MARKET_UNIVERSE:
        errors.append("unknown_market")
    if not raw.period:
        errors.append("period_required")
    if not raw.indicator:
        errors.append("indicator_required")
    if not raw.category:
        errors.append("category_required")
    if not raw.source:
        errors.append("source_required")
    if raw.source in FORBIDDEN_LIVE_SOURCES:
        errors.append("external_live_source_forbidden")
    return {
        "ok": not errors,
        "errors": errors,
        "market": raw.market_key,
        "period": raw.period,
        "indicator": raw.indicator,
    }
