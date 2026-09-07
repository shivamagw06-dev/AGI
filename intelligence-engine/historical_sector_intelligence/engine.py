"""Historical Sector Intelligence Platform engine."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SECTOR_UNIVERSE
from historical_sector_intelligence import traces
from historical_sector_intelligence.gateway import (
    retrieve_events,
    retrieve_history,
    retrieve_sector,
    retrieve_timeline,
    search as gateway_search,
)
from historical_sector_intelligence.pipeline import run_historical_ingestion
from historical_sector_intelligence.schema import (
    HSIP_VERSION,
    NO_HSIP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    STORAGE_NAMESPACES,
)
from historical_sector_intelligence.store import STORE


class HistoricalSectorIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HSIP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HSIP_ACTIONS),
            "ask_triggers_collection": False,
            "immutable_store": True,
            "providers_queried_always": [],
            "namespaces": list(STORAGE_NAMESPACES),
            "supported_sectors": list(SECTOR_UNIVERSE),
            "sector_count": len(SECTOR_UNIVERSE),
            "consumes": [
                "Company Historical Intelligence",
                "Historical Macro (HMIP)",
                "Historical Market tips",
                "Corporate Events",
                "Research History",
                "CSKP universe",
            ],
            "phase": "11.2",
            "preceded_by": ["CSKP 11.1"],
        }

    def run(self, *, sources: list[str] | None = None) -> dict[str, Any]:
        return run_historical_ingestion(sources=sources)

    def history(self, *, limit: int = 200, sector: str | None = None) -> dict[str, Any]:
        return retrieve_history(limit=limit, sector_key=sector)

    def sector(self, name: str, *, limit: int = 300) -> dict[str, Any]:
        return retrieve_sector(name, limit=limit)

    def timeline(self, *, sector: str | None = None, indicator: str | None = None) -> dict[str, Any]:
        return retrieve_timeline(sector=sector, indicator=indicator)

    def events(self, *, sector: str | None = None, limit: int = 100) -> dict[str, Any]:
        return retrieve_events(sector=sector, limit=limit)

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        sector: str | None = None,
        namespace: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return gateway_search(
            q=q, category=category, sector=sector, namespace=namespace, limit=limit
        )

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        timelines = STORE.list_timelines(limit=80)
        avg_complete = (
            round(sum(t.completeness_pct for t in timelines) / len(timelines), 2)
            if timelines
            else 0.0
        )
        # Valuation history tip
        pe_tls = [t for t in timelines if t.indicator == "Average PE"]
        policy_rows = STORE.list_all(limit=40, category="Government")
        event_rows = STORE.list_all(limit=40, category="Events")
        missing = []
        for t in timelines:
            if t.indicator == "Revenue Growth" and t.missing_periods:
                missing.append(
                    {"sector": t.sector_key, "missing": t.missing_periods[:6]}
                )

        return {
            "board": "Historical Sector",
            "programme": PROGRAMME,
            "version": HSIP_VERSION,
            "principles": {
                "immutable_store": True,
                "ask_never_fetches": True,
                "no_external_providers": True,
                "derived_from_agi_platforms": True,
                "checksum_dedupe": True,
            },
            "does_not": list(NO_HSIP_ACTIONS),
            "historical_coverage": cov,
            "years_available": cov.get("years_available"),
            "timeline_completeness": {
                "timelines": len(timelines),
                "average_completeness_pct": avg_complete,
                "sample": [
                    {
                        "sector": t.sector_key,
                        "indicator": t.indicator,
                        "completeness_pct": t.completeness_pct,
                        "years_span": t.years_span,
                    }
                    for t in timelines[:20]
                ],
            },
            "historical_events": [
                {
                    "sector": r.sector_key,
                    "period": r.period,
                    "events": r.key_events,
                }
                for r in event_rows[:20]
            ],
            "policy_history": [
                {
                    "sector": r.sector_key,
                    "period": r.period,
                    "policies": r.government_policies,
                }
                for r in policy_rows[:20]
            ],
            "valuation_history": [
                {
                    "sector": t.sector_key,
                    "nodes": [
                        {"period": n.period, "pe": n.value, "event": n.event}
                        for n in t.nodes
                    ],
                }
                for t in pe_tls[:10]
            ],
            "missing_periods": missing[:20],
            "data_quality": {
                "validation_note": "seeded_derived_series_with_provenance",
                "namespaces": cov.get("by_namespace"),
                "collector_health": STORE.collector_health(),
            },
            "retrieval_performance": {"traces": traces.recent(160)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("total_observations", 0) == 0,
            "providers_queried": [],
        }
