"""Continuous Sector Knowledge Platform engine."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge import traces
from continuous_sector_knowledge.calendar import calendar as sector_calendar
from continuous_sector_knowledge.gateway import (
    retrieve_all,
    retrieve_comparison,
    retrieve_leaders,
    retrieve_sector,
)
from continuous_sector_knowledge.pipeline import run_continuous_ingestion
from continuous_sector_knowledge.schema import (
    CSKP_VERSION,
    NO_CSKP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SECTOR_UNIVERSE,
)
from continuous_sector_knowledge.store import STORE


class ContinuousSectorKnowledgeEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": CSKP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_CSKP_ACTIONS),
            "ask_triggers_collection": False,
            "independent_of": ["Ask", "Research", "Forecast user paths"],
            "providers_queried_always": [],
            "mode": "event_driven_derived",
            "consumes": [
                "Company Knowledge",
                "Macro Knowledge (CMKP)",
                "Market Knowledge",
                "Corporate Events",
                "Research",
                "MRI tips",
            ],
            "supported_sectors": list(SECTOR_UNIVERSE),
            "sector_count": len(SECTOR_UNIVERSE),
            "phase": "11.1",
            "sits_between": ["Macro Intelligence", "Company Intelligence"],
        }

    def run(
        self,
        *,
        sectors: list[str] | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any]:
        """Ops / event-driven refresh — never Ask."""
        return run_continuous_ingestion(sectors=sectors, trigger=trigger)

    def sectors(self, *, limit: int = 100) -> dict[str, Any]:
        return retrieve_all(limit=limit)

    def sector(self, name: str) -> dict[str, Any]:
        return retrieve_sector(name)

    def leaders(self, *, limit: int = 50) -> dict[str, Any]:
        return retrieve_leaders(limit=limit)

    def comparison(self, *, sectors: list[str] | None = None) -> dict[str, Any]:
        return retrieve_comparison(sectors=sectors)

    def calendar(self, *, limit: int = 50) -> dict[str, Any]:
        return sector_calendar(limit=limit)

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        tips = STORE.list_all(limit=40)
        learnings = STORE.learnings(limit=15)
        material = [
            r.to_public_dict()
            for r in tips
            if r.materiality_tier in {"High", "Critical", "Medium"} and r.learning_generated
        ][:15]
        by_sector_companies = {
            r.sector_key: {"label": r.label, "companies": r.leading_companies, "n": r.company_coverage}
            for r in tips
        }
        return {
            "board": "Sector Operations",
            "programme": PROGRAMME,
            "version": CSKP_VERSION,
            "principles": {
                "event_driven": True,
                "derived_not_polled": True,
                "ask_never_fetches": True,
                "ask_never_constructs": True,
                "agi_owned_inputs_only": True,
                "providers_queried_always_empty": True,
            },
            "does_not": list(NO_CSKP_ACTIONS),
            "sector_health": {
                "published": cov.get("published_sectors"),
                "universe": len(SECTOR_UNIVERSE),
                "coverage_pct": round(
                    100.0 * (cov.get("published_sectors") or 0) / max(1, len(SECTOR_UNIVERSE)), 1
                ),
                "outlook_distribution": cov.get("outlook_distribution"),
            },
            "knowledge_coverage": cov,
            "knowledge_freshness": {
                "versions_total": cov.get("versions_total"),
                "latest_run": (STORE.recent_runs(1) or [None])[0],
            },
            "latest_sector_events": [
                {
                    "sector": r.sector_key,
                    "outlook": r.current_outlook,
                    "trigger": r.trigger,
                    "version": r.version,
                }
                for r in sorted(tips, key=lambda x: x.version, reverse=True)[:15]
            ],
            "material_updates": material,
            "research_coverage": {
                "sectors_with_research_tip": sum(
                    1 for r in tips if (r.normalized or {}).get("research")
                ),
                "by_group": cov.get("by_group"),
            },
            "learning_events": [e.to_public_dict() for e in learnings],
            "company_coverage_by_sector": by_sector_companies,
            "builder_health": STORE.builder_health(),
            "retrieval_performance": {"traces": traces.recent(120)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("published_sectors", 0) == 0,
            "calendar": sector_calendar(limit=8).get("calendar"),
            "providers_queried": [],
        }
