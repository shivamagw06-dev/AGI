"""Continuous Market Knowledge Platform engine."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge import traces
from continuous_market_knowledge.gateway import retrieve_all, retrieve_composite, retrieve_domain
from continuous_market_knowledge.pipeline import run_continuous_ingestion
from continuous_market_knowledge.schema import (
    CMKTP_VERSION,
    MARKET_UNIVERSE,
    NO_CMKTP_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from continuous_market_knowledge.store import STORE


class ContinuousMarketKnowledgeEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": CMKTP_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_CMKTP_ACTIONS),
            "ask_triggers_collection": False,
            "independent_of": ["Ask", "Research user paths", "Forecast user paths"],
            "providers_queried_always": [],
            "mode": "event_driven_derived",
            "not_a_market_data_service": True,
            "ops_sources": ["Groww API (Indian live)", "Yahoo Finance (global)", "Internal computations"],
            "consumes": [
                "Groww live tips (ops)",
                "Yahoo global tips (ops)",
                "Macro Knowledge (CMKP)",
                "Sector Knowledge (CSKP)",
                "Sector Forecast (SFI)",
                "Company Knowledge",
                "FPI / LIDI status tips",
            ],
            "supported_domains": list(MARKET_UNIVERSE),
            "domain_count": len(MARKET_UNIVERSE),
            "phase": "12.1",
            "preceded_by": ["Phase 11 Sector Intelligence"],
            "enables": ["Market Historical / Relationships / Analogues / Forecast"],
        }

    def run(
        self,
        *,
        domains: list[str] | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any]:
        """Ops / event-driven refresh — never Ask."""
        return run_continuous_ingestion(domains=domains, trigger=trigger)

    def markets(self, *, limit: int = 100) -> dict[str, Any]:
        return retrieve_all(limit=limit)

    def market(self) -> dict[str, Any]:
        return retrieve_composite()

    def domain(self, name: str) -> dict[str, Any]:
        return retrieve_domain(name)

    def regime(self) -> dict[str, Any]:
        pack = retrieve_domain("india_equity")
        tip = pack.get("latest") or {}
        return {
            "market_regime": tip.get("market_regime"),
            "summary": tip.get("summary"),
            "trend": tip.get("trend"),
            "risk_sentiment": tip.get("risk_sentiment"),
            "health_score": tip.get("health_score"),
            "found": pack.get("found"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "CMKTP_KRIG",
        }

    def breadth(self) -> dict[str, Any]:
        return self._domain_slice("breadth", "breadth")

    def liquidity(self) -> dict[str, Any]:
        return self._domain_slice("liquidity", "liquidity")

    def leadership(self) -> dict[str, Any]:
        return self._domain_slice("leadership", "leadership")

    def flows(self) -> dict[str, Any]:
        return self._domain_slice("institutional_flows", "institutional_flows")

    def volatility(self) -> dict[str, Any]:
        return self._domain_slice("volatility", "volatility")

    def health_score(self) -> dict[str, Any]:
        pack = retrieve_domain("market_health")
        tip = pack.get("latest") or {}
        return {
            "health_score": tip.get("health_score"),
            "market_health": tip.get("market_health"),
            "market_regime": tip.get("market_regime"),
            "risk_sentiment": tip.get("risk_sentiment"),
            "found": pack.get("found"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "CMKTP_KRIG",
        }

    def _domain_slice(self, domain: str, field: str) -> dict[str, Any]:
        pack = retrieve_domain(domain)
        tip = pack.get("latest") or {}
        return {
            "domain": domain,
            field: tip.get(field),
            "market_regime": tip.get("market_regime"),
            "risk_sentiment": tip.get("risk_sentiment"),
            "health_score": tip.get("health_score"),
            "summary": tip.get("summary"),
            "trend": tip.get("trend"),
            "found": pack.get("found"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "CMKTP_KRIG",
        }

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        tips = STORE.list_all(limit=40)
        learnings = STORE.learnings(limit=15)
        composite = retrieve_composite()
        material = [
            r.to_public_dict()
            for r in tips
            if r.materiality_tier in {"High", "Critical", "Medium"} and r.learning_generated
        ][:15]
        return {
            "board": "Market Intelligence Operations",
            "programme": PROGRAMME,
            "version": CMKTP_VERSION,
            "principles": {
                "event_driven": True,
                "derived_not_polled_on_ask": True,
                "ask_never_fetches": True,
                "ask_never_constructs": True,
                "not_a_market_data_service": True,
                "higher_order_concepts_internal": True,
                "providers_queried_always_empty": True,
            },
            "does_not": list(NO_CMKTP_ACTIONS),
            "current_market_regime": (composite.get("market") or {}).get("market_regime"),
            "market_health_score": (composite.get("market") or {}).get("health_score"),
            "breadth_dashboard": (composite.get("market") or {}).get("breadth"),
            "liquidity_dashboard": (composite.get("market") or {}).get("liquidity"),
            "institutional_flows": (composite.get("market") or {}).get("institutional_flows"),
            "sector_leadership": (composite.get("market") or {}).get("leadership"),
            "cross_asset_dashboard": (composite.get("market") or {}).get("cross_asset_state"),
            "risk_sentiment": (composite.get("market") or {}).get("risk_sentiment"),
            "latest_material_events": material or [e.to_public_dict() for e in learnings],
            "knowledge_freshness": {
                "domains_published": cov.get("published_domains"),
                "versions_total": cov.get("versions_total"),
                "latest_run": (STORE.recent_runs(1) or [None])[0],
            },
            "collection_status": {
                "mode": "event_driven_derived",
                "builder_health": STORE.builder_health(),
                "ops_sources": ["Groww", "Yahoo", "Internal"],
            },
            "publication_status": cov,
            "knowledge_coverage": cov,
            "retrieval_performance": {"traces": traces.recent(40)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("published_domains", 0) == 0,
            "phase": "12.1",
            "providers_queried": [],
        }
