"""HMIP engine — immutable historical macro memory."""

from __future__ import annotations

from typing import Any

from historical_macro_intelligence import traces
from historical_macro_intelligence.gateway import (
    retrieve_country,
    retrieve_history,
    retrieve_indicator,
    retrieve_timeline,
    search,
)
from historical_macro_intelligence.pipeline import run_historical_ingestion
from historical_macro_intelligence.schema import (
    HMIP_VERSION,
    NO_HMIP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SOURCES,
    STORAGE_NAMESPACES,
)
from historical_macro_intelligence.store import STORE


class HistoricalMacroIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMIP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HMIP_ACTIONS),
            "immutable_store": True,
            "sources": list(SOURCES),
            "namespaces": list(STORAGE_NAMESPACES),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "phase": "10.2",
            "preceded_by": "CMKP 10.1",
        }

    def run(self, *, sources: list[str] | None = None) -> dict[str, Any]:
        return run_historical_ingestion(sources=sources)

    def history(self, *, limit: int = 200, country: str | None = None) -> dict[str, Any]:
        return retrieve_history(limit=limit, country=country)

    def indicator(self, indicator: str, *, country: str = "India") -> dict[str, Any]:
        return retrieve_indicator(indicator, country=country)

    def country(self, country: str, *, limit: int = 300) -> dict[str, Any]:
        return retrieve_country(country, limit=limit)

    def timeline(self, *, indicator: str | None = None, country: str = "India") -> dict[str, Any]:
        return retrieve_timeline(indicator=indicator, country=country)

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        country: str | None = None,
        namespace: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return search(
            q=q, category=category, country=country, namespace=namespace, limit=limit
        )

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        timelines = STORE.list_timelines(limit=50)
        avg_complete = (
            round(sum(t.completeness_pct for t in timelines) / len(timelines), 2)
            if timelines
            else 0.0
        )
        missing = []
        for t in timelines:
            if t.missing_periods:
                missing.append(
                    {
                        "indicator": t.indicator,
                        "country": t.country,
                        "missing_periods": t.missing_periods,
                    }
                )
        return {
            "board": "Historical Macro",
            "programme": PROGRAMME,
            "version": HMIP_VERSION,
            "principles": {
                "immutable_historical_memory": True,
                "never_overwrite": True,
                "ask_never_fetches": True,
                "analysis_uses_store_only": True,
                "providers_queried_always_empty": True,
            },
            "does_not": list(NO_HMIP_ACTIONS),
            "historical_coverage": cov,
            "years_available": cov.get("years_available"),
            "missing_periods": missing[:30],
            "timeline_completeness": {
                "timelines": len(timelines),
                "average_completeness_pct": avg_complete,
                "sample": [
                    {
                        "indicator": t.indicator,
                        "country": t.country,
                        "completeness_pct": t.completeness_pct,
                        "nodes": len(t.nodes),
                        "years_span": t.years_span,
                    }
                    for t in timelines[:20]
                ],
            },
            "data_quality": {
                "collector_health": STORE.collector_health(),
                "validation_note": "official_seeded_series_with_provenance",
            },
            "revision_history": STORE.revision_history(limit=30),
            "storage_growth": {
                "total_observations": cov.get("total_observations"),
                "by_namespace": cov.get("by_namespace"),
            },
            "recent_runs": STORE.recent_runs(10),
            "retrieval_performance": {"traces": traces.recent(100)},
            "ingestion_idle": cov.get("total_observations", 0) == 0,
            "phase": "10.2",
            "note": "Read APIs never collect. Use POST /v1/macro/history/run for ingestion.",
        }
