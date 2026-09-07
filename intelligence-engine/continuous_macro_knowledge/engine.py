"""CMKP engine — continuous background macro knowledge platform."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge import traces
from continuous_macro_knowledge.calendar import calendar
from continuous_macro_knowledge.gateway import (
    retrieve_global,
    retrieve_india,
    retrieve_indicator,
    retrieve_releases,
)
from continuous_macro_knowledge.pipeline import run_continuous_ingestion
from continuous_macro_knowledge.schema import (
    CATEGORIES,
    CMKP_VERSION,
    COLLECTION_SCHEDULE,
    NO_CMKP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SOURCES,
)
from continuous_macro_knowledge.store import STORE


class ContinuousMacroKnowledgeEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": CMKP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_CMKP_ACTIONS),
            "independent_of": ["Ask", "Research", "Forecast"],
            "sources": [s["source_id"] for s in SOURCES],
            "categories": list(CATEGORIES),
            "ask_triggers_collection": False,
        }

    def run(self, *, sources: list[str] | None = None) -> dict[str, Any]:
        """Ops / scheduler entrypoint — never Ask."""
        return run_continuous_ingestion(sources=sources)

    def india(self, *, limit: int = 100) -> dict[str, Any]:
        """Read published India macro knowledge only — never collects."""
        return retrieve_india(limit=limit)

    def global_macro(self, *, limit: int = 100) -> dict[str, Any]:
        """Read published global macro knowledge only — never collects."""
        return retrieve_global(limit=limit)

    def indicator(self, indicator: str, *, country: str | None = None) -> dict[str, Any]:
        """Read a published indicator — never collects on miss."""
        return retrieve_indicator(indicator, country=country)

    def releases(self, *, limit: int = 50) -> dict[str, Any]:
        return retrieve_releases(limit=limit)

    def release_calendar(self, *, limit: int = 50) -> dict[str, Any]:
        return calendar(limit=limit)

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        health = STORE.collector_health()
        published = STORE.published(limit=15)
        learnings = STORE.learnings(limit=15)
        missing = self._missing_indicators()
        return {
            "board": "Macro Operations",
            "programme": PROGRAMME,
            "version": CMKP_VERSION,
            "principles": {
                "continuous_background": True,
                "ask_never_fetches": True,
                "research_never_fetches": True,
                "forecast_never_fetches": True,
                "material_learning_only": True,
                "versioned_mko": True,
            },
            "does_not": list(NO_CMKP_ACTIONS),
            "collector_health": health,
            "latest_releases": [p.to_public_dict() for p in published],
            "upcoming_releases": calendar(limit=10).get("calendar"),
            "freshness": {
                "published_objects": cov.get("published_objects"),
                "rule": "background_collectors_own_freshness",
            },
            "missing_indicators": missing,
            "publication_status": {
                "recent": STORE.publications(20),
                "total_published": cov.get("published_objects"),
            },
            "learning_events": [l.model_dump(mode="json") for l in learnings],
            "materiality": {
                "recent_tiers": [p.materiality_tier for p in published],
                "learning_count": cov.get("learning_events"),
            },
            "knowledge_coverage": cov,
            "collection_schedule": COLLECTION_SCHEDULE,
            "sources": list(SOURCES),
            "recent_runs": STORE.recent_runs(10),
            "retrieval_performance": {"traces": traces.recent(120)},
            "phase": "10.1",
            "ingestion_idle": cov.get("total_objects", 0) == 0,
            "note": "Read APIs never trigger collectors. Use POST /v1/macro/run (ops/scheduler) to ingest.",
        }

    def _missing_indicators(self) -> list[str]:
        expected = {
            "India:Repo Rate",
            "India:CPI",
            "India:WPI",
            "India:GDP",
            "India:IIP",
            "India:Fiscal Deficit",
            "India:GST Collections",
            "India:Forex Reserves",
            "United States:Federal Funds Rate",
            "Global:WEO Global Growth",
        }
        have = {f"{m.country}:{m.indicator}" for m in STORE.published(limit=500)}
        return sorted(expected - have)
