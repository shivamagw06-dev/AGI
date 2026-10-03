"""Publish provider raw inputs into AGI Company / Market knowledge layers."""

from __future__ import annotations

from typing import Any

from forecast_provider_integration import traces
from forecast_provider_integration.gateways.bse import BseActionsGateway
from forecast_provider_integration.gateways.company_ir import CompanyIrGateway
from forecast_provider_integration.gateways.nse import NseDisclosureGateway
from forecast_provider_integration.gateways.yahoo import YahooFinancialGateway
from forecast_provider_integration.market_snapshot import ensure_fresh_market_snapshot
from forecast_provider_integration.schema import (
    CompanyKnowledgeObject,
    DynamicMarketState,
    StaticKnowledge,
)
from forecast_provider_integration.store import STORE

_YAHOO = YahooFinancialGateway()
_NSE = NseDisclosureGateway()
_BSE = BseActionsGateway()
_IR = CompanyIrGateway()


def publish_company_knowledge(
    entity: str,
    *,
    refresh_market: bool = True,
    catalog_tip: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest Yahoo/NSE/BSE/IR (+ Groww snapshot) into layered Company Knowledge."""
    span = traces.begin("knowledge_refresh", meta={"entity": entity, "kind": "company"})
    key = entity.upper()

    yspan = traces.begin("yahoo_financial_refresh", meta={"entity": key})
    static = _YAHOO.fetch_static(key)
    # Merge catalog tip business fields when provided (IFI seeds)
    if catalog_tip:
        profile = dict(static.business_profile)
        for k in ("name", "sector", "business_profile", "sector_key"):
            if catalog_tip.get(k) and k not in profile:
                profile[k if k != "business_profile" else "summary"] = catalog_tip.get(k)
        if catalog_tip.get("name"):
            profile["name"] = catalog_tip["name"]
        if catalog_tip.get("sector"):
            profile["sector"] = catalog_tip["sector"]
        if catalog_tip.get("business_profile"):
            profile["summary"] = catalog_tip["business_profile"]
        static = StaticKnowledge(
            business_profile=profile,
            financial_statements=static.financial_statements,
            historical_financials=static.historical_financials,
            historical_valuation={
                **static.historical_valuation,
                **(catalog_tip.get("valuation") or {}),
            },
            historical_ratios=static.historical_ratios,
            historical_ownership=static.historical_ownership,
            historical_relationships=list(static.historical_relationships),
            historical_analogues=list(static.historical_analogues),
            research={
                **static.research,
                "investment_thesis_tip": catalog_tip.get("investment_thesis"),
                "decision_status": catalog_tip.get("decision_status"),
            },
            primary_sources=["yahoo", "company_ir", "nse", "bse", "agi_catalog"],
            updated_at=static.updated_at,
            freshness_sec=0,
        )
    STORE.tick_collector("yahoo", ok=True, meta={"entity": key})
    traces.end(yspan, output={"statements": bool(static.financial_statements)})

    nse = _NSE.collect(key)
    STORE.tick_collector("nse", ok=True, meta={"events": len(nse.get("events") or [])})
    bse = _BSE.collect(key)
    STORE.tick_collector("bse", ok=True, meta={"events": len(bse.get("events") or [])})
    ir = _IR.collect(key)
    STORE.tick_collector("company_ir", ok=True, meta={"docs": len(ir.get("documents") or [])})

    # Attach IR / exchange tips into research
    static.research = {
        **static.research,
        "nse_events": nse.get("events") or [],
        "bse_events": bse.get("events") or [],
        "company_ir_documents": ir.get("documents") or [],
    }

    snapshot = None
    refresh_meta = None
    if refresh_market:
        refresh_meta = ensure_fresh_market_snapshot(key, scope="company")
        snap_dict = refresh_meta.get("snapshot") or {}
        from forecast_provider_integration.schema import MarketSnapshot

        snapshot = MarketSnapshot.model_validate(snap_dict) if snap_dict else None

    obj = CompanyKnowledgeObject(
        entity=key,
        static=static,
        dynamic=DynamicMarketState(
            snapshot=snapshot,
            primary_source="groww",
            fallback_source="yahoo",
            updated_at=snapshot.as_of if snapshot else None,
            stale=bool(snapshot.stale) if snapshot else True,
        ),
        knowledge_confidence=0.82 if static.financial_statements else 0.55,
    )
    published = STORE.publish_company(obj)
    traces.end(
        span,
        output={
            "entity": key,
            "has_snapshot": snapshot is not None,
            "confidence": published.knowledge_confidence,
        },
    )
    out = published.to_public_dict()
    out["refresh"] = refresh_meta
    return out
