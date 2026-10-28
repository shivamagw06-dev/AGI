"""Forecast Provider Integration engine — India-first Knowledge Platform path."""

from __future__ import annotations

from typing import Any

from forecast_provider_integration import traces
from forecast_provider_integration.bridge import enrich_forecast_inputs, get_published_company
from forecast_provider_integration.health import provider_health
from forecast_provider_integration.market_snapshot import ensure_fresh_market_snapshot
from forecast_provider_integration.publish import publish_company_knowledge
from forecast_provider_integration.schema import (
    FPI_VERSION,
    FORECAST_FORBIDDEN_DIRECT_CALLS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    PROVIDER_PRIORITY,
    REFRESH_POLICY,
)
from forecast_provider_integration.store import STORE


class ForecastProviderIntegrationEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": FPI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "forecast_direct_provider_calls": False,
            "forbidden_on_forecast_path": list(FORECAST_FORBIDDEN_DIRECT_CALLS),
            "primary_live_market": "groww",
            "primary_research": "yahoo",
            "disclosures": ["nse", "bse"],
            "documents": "company_ir",
            "controlled_refresh": "market_snapshot_when_stale",
        }

    def dashboard(self) -> dict[str, Any]:
        health = provider_health()
        return {
            "board": "Forecast Provider Integration",
            "programme": PROGRAMME,
            "version": FPI_VERSION,
            "principles": {
                "providers_supply_raw": True,
                "knowledge_platform_transforms": True,
                "forecast_never_reasons_over_raw_apis": True,
                "groww_primary_live": True,
                "yahoo_research_historical": True,
                "stale_snapshot_refresh_only": True,
            },
            "provider_priority": list(PROVIDER_PRIORITY),
            "refresh_policy": REFRESH_POLICY,
            **health,
            "recent_publish_events": STORE.recent_events(20),
            "retrieval_performance": {"traces": traces.recent(50)},
        }

    def publish_company(self, entity: str, *, catalog_tip: dict[str, Any] | None = None) -> dict[str, Any]:
        return publish_company_knowledge(entity, catalog_tip=catalog_tip)

    def refresh_snapshot(self, entity: str, *, scope: str = "company", force: bool = False) -> dict[str, Any]:
        return ensure_fresh_market_snapshot(entity, scope=scope, force=force)

    def company_knowledge(self, entity: str) -> dict[str, Any]:
        published = get_published_company(entity)
        if published:
            return {"found": True, **published}
        return {"found": False, "entity": entity.upper(), "object": self.publish_company(entity)}

    def enrich_for_forecast(
        self,
        *,
        scope: str,
        entity: str,
        catalog_current: dict[str, Any] | None = None,
        catalog_market: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return enrich_forecast_inputs(
            scope=scope,
            entity=entity,
            catalog_current=catalog_current,
            catalog_market=catalog_market,
        )
