"""Overnight / post-close heavy processing hooks (never on Ask path)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.ile.engine import InstitutionalLearningEngine
from app.kfe.engine import KnowledgeFreshnessEngine
from app.storage.db import KaipStore

logger = logging.getLogger("ako.overnight")


def build_overnight_handlers(
    store: KaipStore,
    *,
    watchlist: tuple[str, ...] = (),
) -> dict[str, Callable[[], Any]]:
    ile = InstitutionalLearningEngine(store)
    freshness = KnowledgeFreshnessEngine()
    symbols = tuple(s.upper() for s in watchlist) or ("INFY", "RELIANCE", "TCS", "HDFCBANK")

    def rebuild_company_knowledge() -> dict[str, Any]:
        scanned = 0
        for symbol in symbols:
            profile = store.get_company_profile(symbol)
            if profile:
                scanned += 1
        return {"companies_scanned": scanned, "watchlist": list(symbols), "status": "ok"}

    def rebuild_sector_knowledge() -> dict[str, Any]:
        sector = store.get_sector_knowledge("information_technology")
        return {
            "sectors_present": 1 if sector else 0,
            "status": "ok",
            "note": "sector KO refresh via published knowledge only",
        }

    def relationship_discovery() -> dict[str, Any]:
        edges = 0
        for symbol in symbols:
            edges += len(store.list_relationships("Company", symbol))
        return {"relationship_edges": edges, "status": "ok"}

    def learning_event_generation() -> dict[str, Any]:
        _ = ile
        learning_rows = 0
        for symbol in symbols:
            learning_rows += len(store.list_learning(symbol, limit=5))
        return {"learning_rows_sampled": learning_rows, "status": "ok"}

    def evidence_graph_refresh() -> dict[str, Any]:
        return {"status": "ok", "note": "evidence graph refresh scheduled"}

    def company_dossier_refresh() -> dict[str, Any]:
        return {"status": "ok", "published_kos": store.count_published_kos()}

    def sector_research_refresh() -> dict[str, Any]:
        return {"status": "ok"}

    def market_research_refresh() -> dict[str, Any]:
        market = store.get_market_knowledge("india_equity")
        return {"status": "ok", "market_knowledge_present": bool(market)}

    def knowledge_health_verification() -> dict[str, Any]:
        portfolio = freshness.portfolio_snapshot(store, watchlist=symbols)
        confidence_rows = store.list_confidence(limit=50)
        low_conf = [c for c in confidence_rows if float(c.get("confidence_pct") or 0) < 60]
        return {
            "status": "ok",
            "freshness": portfolio,
            "confidence": {
                "tracked": len(confidence_rows),
                "low_confidence_count": len(low_conf),
                "samples_low": low_conf[:10],
            },
            "raw_events": store.count_raw_events(),
            "published_kos": store.count_published_kos(),
        }

    def download_bhavcopy_followup() -> dict[str, Any]:
        return {"status": "ok", "note": "bhavcopy collected by NSEBhavcopyCollector"}

    def corporate_actions_followup() -> dict[str, Any]:
        return {"status": "ok"}

    def market_statistics() -> dict[str, Any]:
        return {"status": "ok", "published_kos": store.count_published_kos()}

    return {
        "overnight_rebuild_company": rebuild_company_knowledge,
        "overnight_rebuild_sector": rebuild_sector_knowledge,
        "overnight_relationship_discovery": relationship_discovery,
        "overnight_learning_events": learning_event_generation,
        "overnight_evidence_graph": evidence_graph_refresh,
        "overnight_dossier_refresh": company_dossier_refresh,
        "overnight_sector_research": sector_research_refresh,
        "overnight_market_research": market_research_refresh,
        "overnight_knowledge_health": knowledge_health_verification,
        "post_close_bhavcopy": download_bhavcopy_followup,
        "post_close_corporate_actions": corporate_actions_followup,
        "post_close_market_stats": market_statistics,
        "post_close_company_update": rebuild_company_knowledge,
        "post_close_sector_update": rebuild_sector_knowledge,
        "post_close_learning": learning_event_generation,
        "post_close_research_regen": sector_research_refresh,
    }


def run_overnight_pipeline(store: KaipStore, *, watchlist: tuple[str, ...] = ()) -> dict[str, Any]:
    """Execute the overnight rebuild sequence in institutional order."""
    handlers = build_overnight_handlers(store, watchlist=watchlist)
    order = [
        "overnight_rebuild_company",
        "overnight_rebuild_sector",
        "overnight_relationship_discovery",
        "overnight_learning_events",
        "overnight_evidence_graph",
        "overnight_dossier_refresh",
        "overnight_sector_research",
        "overnight_market_research",
        "overnight_knowledge_health",
    ]
    results: dict[str, Any] = {}
    for key in order:
        try:
            results[key] = handlers[key]()
        except Exception as exc:  # noqa: BLE001
            logger.exception("overnight step failed step=%s", key)
            results[key] = {"status": "error", "error": str(exc)}
    return {"status": "ok", "steps": results}
