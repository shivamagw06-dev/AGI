"""IFI production facade — Forecast Bundle preparation for APIs / Mission Control."""

from __future__ import annotations

from typing import Any

from institutional_forecast_intelligence.engine import InstitutionalForecastEngine
from institutional_forecast_intelligence.schema import (
    IFI_VERSION,
    NO_IFI_JUDGMENT,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
)

_ENGINE = InstitutionalForecastEngine()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "version": IFI_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "does_not": list(NO_IFI_JUDGMENT),
        "providers_queried_always": [],
        "hip_bridge_enabled": _ENGINE.hip.enabled,
        "provider_integration": "fpi",
        "controlled_refresh": "market_snapshot_when_stale",
        "forecast_direct_provider_calls": False,
    }


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def company(ticker: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.company_bundle(ticker, question=question)


def sector(sector_key: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.sector_bundle(sector_key, question=question)


def market(*, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.market_bundle(question=question)


def macro(*, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.macro_bundle(question=question)


def theme(theme_key: str = "artificial_intelligence", *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.theme_bundle(theme_key, question=question)


def bundle(*, scope: str, entity: str | None = None, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.bundle(scope=scope, entity=entity, question=question)
