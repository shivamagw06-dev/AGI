"""Historical Market Intelligence Platform engine."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MARKET_UNIVERSE
from historical_market_intelligence import traces
from historical_market_intelligence.gateway import (
    retrieve_by_category,
    retrieve_history,
    retrieve_market,
    retrieve_regimes,
    retrieve_timeline,
    search as gateway_search,
)
from historical_market_intelligence.pipeline import run_historical_ingestion
from historical_market_intelligence.schema import (
    HMKIP_VERSION,
    NO_HMKIP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    STORAGE_NAMESPACES,
)
from historical_market_intelligence.store import STORE


class HistoricalMarketIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMKIP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HMKIP_ACTIONS),
            "ask_triggers_collection": False,
            "immutable_store": True,
            "providers_queried_always": [],
            "namespaces": list(STORAGE_NAMESPACES),
            "supported_markets": list(MARKET_UNIVERSE),
            "market_count": len(MARKET_UNIVERSE),
            "consumes": [
                "CMKTP continuous market knowledge",
                "Historical Macro (HMIP)",
                "Historical Sector (HSIP)",
                "Groww Historical (ops seed labels)",
                "Yahoo Finance Historical (ops seed labels)",
            ],
            "phase": "12.2",
            "preceded_by": ["CMKTP 12.1"],
        }

    def run(
        self, *, sources: list[str] | None = None, markets: list[str] | None = None
    ) -> dict[str, Any]:
        return run_historical_ingestion(sources=sources, markets=markets)

    def history(self, *, limit: int = 200, market: str | None = None) -> dict[str, Any]:
        return retrieve_history(limit=limit, market_key=market)

    def market(self, name: str, *, limit: int = 300) -> dict[str, Any]:
        return retrieve_market(name, limit=limit)

    def timeline(
        self, *, market: str | None = None, indicator: str | None = None
    ) -> dict[str, Any]:
        return retrieve_timeline(market=market, indicator=indicator)

    def regimes(self, *, market: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_regimes(market=market, limit=limit)

    def breadth(self, *, market: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_by_category("Breadth", market=market, limit=limit)

    def liquidity(self, *, market: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_by_category("Liquidity", market=market, limit=limit)

    def volatility(self, *, market: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_by_category("Volatility", market=market, limit=limit)

    def flows(self, *, market: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_by_category("Flows", market=market, limit=limit)

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        market: str | None = None,
        namespace: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return gateway_search(
            q=q, category=category, market=market, namespace=namespace, limit=limit
        )

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        timelines = STORE.list_timelines(limit=80)
        avg_complete = (
            round(sum(t.completeness_pct for t in timelines) / len(timelines), 2)
            if timelines
            else 0.0
        )
        missing = []
        for t in timelines:
            if t.indicator == "Market Health" and t.missing_periods:
                missing.append({"market": t.market_key, "missing": t.missing_periods[:8]})

        regime_rows = STORE.list_all(limit=40, category="Cycles")
        breadth_rows = STORE.list_all(limit=20, category="Breadth")
        liquidity_rows = STORE.list_all(limit=20, category="Liquidity")
        vol_rows = STORE.list_all(limit=20, category="Volatility")
        flow_rows = STORE.list_all(limit=20, category="Flows")
        xasset_rows = STORE.list_all(limit=20, category="CrossAsset")

        return {
            "board": "Historical Market",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMKIP_VERSION,
            "principles": {
                "immutable_store": True,
                "ask_never_fetches": True,
                "no_external_providers": True,
                "derived_from_agi_platforms": True,
                "checksum_dedupe": True,
            },
            "does_not": list(NO_HMKIP_ACTIONS),
            "historical_coverage": cov,
            "years_available": cov.get("years_available"),
            "timeline_completeness": {
                "timelines": len(timelines),
                "average_completeness_pct": avg_complete,
                "sample": [
                    {
                        "market": t.market_key,
                        "indicator": t.indicator,
                        "completeness_pct": t.completeness_pct,
                        "years_span": t.years_span,
                    }
                    for t in timelines[:20]
                ],
            },
            "regime_history": [
                {
                    "market": r.market_key,
                    "period": r.period,
                    "regime": r.market_regime,
                    "events": r.major_events,
                }
                for r in regime_rows[:20]
            ],
            "breadth_history": [
                {"market": r.market_key, "period": r.period, "value": r.value}
                for r in breadth_rows
            ],
            "liquidity_history": [
                {"market": r.market_key, "period": r.period, "value": r.value}
                for r in liquidity_rows
            ],
            "volatility_history": [
                {"market": r.market_key, "period": r.period, "value": r.value}
                for r in vol_rows
            ],
            "flow_history": [
                {"market": r.market_key, "period": r.period, "value": r.value, "tone": r.institutional_flows}
                for r in flow_rows
            ],
            "cross_asset_history": [
                {"market": r.market_key, "period": r.period, "state": r.cross_asset_state, "value": r.value}
                for r in xasset_rows
            ],
            "missing_periods": missing[:20],
            "data_quality": {
                "validation_note": "seeded_derived_series_with_provenance",
                "namespaces": cov.get("by_namespace"),
                "collector_health": STORE.collector_health(),
            },
            "knowledge_freshness": {
                "mode": "historical_seed",
                "last_runs": STORE.recent_runs(3),
            },
            "retrieval_performance": {"traces": traces.recent(160)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("total_observations", 0) == 0,
            "providers_queried": [],
            "phase": "12.2",
        }
