"""Soft bridge from Knowledge Platform → Forecast Bundle inputs.

IFI calls this module only. It never imports Groww/Yahoo/NSE/BSE gateways
for uncontrolled calls — market refresh is gated by staleness.
"""

from __future__ import annotations

from typing import Any

from forecast_provider_integration import traces
from forecast_provider_integration.market_snapshot import ensure_fresh_market_snapshot
from forecast_provider_integration.publish import publish_company_knowledge
from forecast_provider_integration.schema import FORECAST_FORBIDDEN_DIRECT_CALLS
from forecast_provider_integration.store import STORE


def enrich_forecast_inputs(
    *,
    scope: str,
    entity: str,
    catalog_current: dict[str, Any] | None = None,
    catalog_market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach layered Company Knowledge + fresh-enough Market Snapshot for bundles."""
    span = traces.begin(
        "forecast_bundle_generation",
        meta={"scope": scope, "entity": entity, "phase": "provider_enrichment"},
    )
    scope_l = (scope or "company").lower()
    key = (entity or "INFY").upper()

    # Guard: forecast path must not claim direct provider calls
    providers_queried: list[str] = []

    company_ko = None
    market_snap = None
    refresh_meta = None

    if scope_l in {"company", "sector"}:
        # Publish/refresh AGI knowledge (Yahoo static + Groww dynamic if stale)
        company_ko = publish_company_knowledge(
            key if scope_l == "company" else (catalog_current or {}).get("ticker") or "INFY",
            refresh_market=True,
            catalog_tip=catalog_current if scope_l == "company" else None,
        )
        refresh_meta = company_ko.get("refresh")
        market_snap = (company_ko.get("dynamic") or {}).get("snapshot")
    elif scope_l == "market":
        refresh_meta = ensure_fresh_market_snapshot("NIFTY", scope="market")
        market_snap = refresh_meta.get("snapshot")
        # Soft publish index as market knowledge tip
        company_ko = {
            "entity": "NIFTY",
            "static": {"business_profile": {"name": "NIFTY 50"}, "primary_sources": ["groww", "yahoo"]},
            "dynamic": {"snapshot": market_snap, "primary_source": "groww"},
        }
    else:
        # macro/theme — no live market required; still record knowledge freshness tip
        refresh_meta = {"refreshed": False, "reason": "scope_does_not_require_live_snapshot"}

    # Layer catalog current knowledge with static/dynamic split
    layered_current = dict(catalog_current or {})
    if company_ko and scope_l == "company":
        layered_current = {
            **layered_current,
            "static_knowledge": company_ko.get("static"),
            "dynamic_market_state": company_ko.get("dynamic"),
            "market_snapshot": market_snap,
            "knowledge_confidence": company_ko.get("knowledge_confidence"),
            "knowledge_layers": {"static": True, "dynamic": True},
            "provider_architecture": "india_first_knowledge_platform",
        }

    market_intel = dict(catalog_market or {})
    if market_snap:
        market_intel = {
            **market_intel,
            "live_snapshot": market_snap,
            "live_source_provider": (market_snap or {}).get("source_provider"),
            "live_fallback_used": (market_snap or {}).get("fallback_used"),
            "liquidity_tip": market_intel.get("liquidity") or "Adequate",
        }

    freshness = {
        "market_snapshot": {
            "age_sec": (refresh_meta or {}).get("age_sec"),
            "refreshed": (refresh_meta or {}).get("refreshed"),
            "stale_after_sec": (refresh_meta or {}).get("stale_after_sec"),
            "provider": (refresh_meta or {}).get("provider_called"),
        },
        "static_knowledge": "yahoo_daily_event",
        "corporate_events": "nse_bse_30s_collectors",
        "company_ir": "10m_market_hours",
        "rule": "Forecast consumes AGI knowledge; live snapshot refreshed only when stale",
    }

    out = {
        "current_knowledge": layered_current,
        "market_intelligence": market_intel,
        "market_snapshot": market_snap,
        "company_knowledge_object": company_ko,
        "knowledge_freshness": freshness,
        "providers_queried": providers_queried,
        "forbidden_direct_calls": list(FORECAST_FORBIDDEN_DIRECT_CALLS),
        "refresh": refresh_meta,
        "sources_added": ["agi_knowledge_platform", "fpi_market_snapshot"],
    }
    traces.end(
        span,
        output={
            "scope": scope_l,
            "has_snapshot": market_snap is not None,
            "refreshed": bool((refresh_meta or {}).get("refreshed")),
            "providers_queried": providers_queried,
        },
    )
    return out


def get_published_company(entity: str) -> dict[str, Any] | None:
    obj = STORE.get_company(entity)
    return obj.to_public_dict() if obj else None
