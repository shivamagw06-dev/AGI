"""Provider health aggregation for Mission Control."""

from __future__ import annotations

from typing import Any

from forecast_provider_integration.gateways.bse import BseActionsGateway
from forecast_provider_integration.gateways.company_ir import CompanyIrGateway
from forecast_provider_integration.gateways.groww import GrowwMarketGateway
from forecast_provider_integration.gateways.nse import NseDisclosureGateway
from forecast_provider_integration.gateways.yahoo import YahooFinancialGateway
from forecast_provider_integration.market_snapshot import _age_sec, is_stale
from forecast_provider_integration.schema import PROVIDER_PRIORITY, REFRESH_POLICY, ProviderHealth
from forecast_provider_integration.store import STORE


def provider_health() -> dict[str, Any]:
    groww = GrowwMarketGateway().health()
    yahoo = YahooFinancialGateway().health()
    nse = NseDisclosureGateway().health()
    bse = BseActionsGateway().health()
    ir = CompanyIrGateway().health()

    ticks = STORE.collector_ticks()
    failovers = STORE.failover_events(20)

    # Snapshot freshness sample (INFY / NIFTY if present)
    snap_ages = {}
    for ent in ("INFY", "NIFTY", "TCS"):
        snap = STORE.get_snapshot(ent)
        if snap:
            snap_ages[ent] = {
                "age_sec": _age_sec(snap.as_of),
                "stale": is_stale(snap),
                "provider": snap.source_provider,
                "ltp": snap.ltp,
            }

    # Knowledge freshness from company objects
    knowledge_ages = {}
    for ent in ("INFY", "TCS", "HDFCBANK"):
        obj = STORE.get_company(ent)
        if obj:
            knowledge_ages[ent] = {
                "static_updated_at": obj.static.updated_at.isoformat() if obj.static.updated_at else None,
                "dynamic_stale": obj.dynamic.stale,
                "confidence": obj.knowledge_confidence,
            }

    rows = [
        ProviderHealth(
            provider="groww",
            status=groww.get("status") or "unknown",
            configured=bool(groww.get("configured")),
            connection=str(groww.get("connection") or "unknown"),
            websocket_latency_ms=None,
            snapshot_freshness_sec=(snap_ages.get("INFY") or {}).get("age_sec"),
            last_success_at=None,
            failover_events=sum(1 for f in failovers if f.from_provider == "groww"),
            detail=str(groww.get("detail") or ""),
            role="primary_live_market",
        ),
        ProviderHealth(
            provider="yahoo",
            status=yahoo.get("status") or "unknown",
            configured=bool(yahoo.get("configured")),
            connection=str(yahoo.get("connection") or "unknown"),
            knowledge_freshness_sec=0,
            detail=str(yahoo.get("detail") or ""),
            role="research_and_historical",
        ),
        ProviderHealth(
            provider="nse",
            status=nse.get("status") or "unknown",
            configured=True,
            connection="collector",
            detail=str(nse.get("detail") or ""),
            role="official_disclosure",
        ),
        ProviderHealth(
            provider="bse",
            status=bse.get("status") or "unknown",
            configured=True,
            connection="collector",
            detail=str(bse.get("detail") or ""),
            role="corporate_actions",
        ),
        ProviderHealth(
            provider="company_ir",
            status=ir.get("status") or "unknown",
            configured=True,
            connection="collector",
            detail=str(ir.get("detail") or ""),
            role="official_documents",
        ),
    ]

    return {
        "board": "Forecast Provider Health",
        "providers": [r.model_dump(mode="json") for r in rows],
        "groww_connection_status": groww.get("status"),
        "yahoo_finance_status": yahoo.get("status"),
        "nse_collector_status": nse.get("status"),
        "bse_collector_status": bse.get("status"),
        "company_ir_collector_status": ir.get("status"),
        "websocket_latency_ms": None,
        "websocket_supported": True,
        "snapshot_freshness": snap_ages,
        "knowledge_freshness": knowledge_ages,
        "provider_failover_events": [f.model_dump(mode="json") for f in failovers],
        "collector_ticks": ticks,
        "refresh_policy": REFRESH_POLICY,
        "provider_priority": list(PROVIDER_PRIORITY),
        "forecast_may_call_providers_directly": False,
    }
