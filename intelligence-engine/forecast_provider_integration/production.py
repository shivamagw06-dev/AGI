"""FPI production facade."""

from __future__ import annotations

from typing import Any

from forecast_provider_integration.engine import ForecastProviderIntegrationEngine

_ENGINE = ForecastProviderIntegrationEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def provider_health() -> dict[str, Any]:
    from forecast_provider_integration.health import provider_health as _ph

    return _ph()


def publish_company(entity: str, *, catalog_tip: dict[str, Any] | None = None) -> dict[str, Any]:
    return _ENGINE.publish_company(entity, catalog_tip=catalog_tip)


def refresh_snapshot(entity: str, *, scope: str = "company", force: bool = False) -> dict[str, Any]:
    return _ENGINE.refresh_snapshot(entity, scope=scope, force=force)


def company_knowledge(entity: str) -> dict[str, Any]:
    return _ENGINE.company_knowledge(entity)


def enrich_for_forecast(
    *,
    scope: str,
    entity: str,
    catalog_current: dict[str, Any] | None = None,
    catalog_market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _ENGINE.enrich_for_forecast(
        scope=scope,
        entity=entity,
        catalog_current=catalog_current,
        catalog_market=catalog_market,
    )
