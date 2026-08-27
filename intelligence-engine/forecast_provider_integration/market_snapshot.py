"""Controlled live market snapshot refresh — sole external refresh allowed on forecast path.

Flow:
  Company Knowledge → Market Snapshot → If stale → Refresh Live Snapshot → Continue Forecast

Forecast modules call this knowledge-layer helper; they never import Groww/Yahoo clients.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from forecast_provider_integration import traces
from forecast_provider_integration.gateways.groww import GrowwMarketGateway
from forecast_provider_integration.gateways.yahoo import YahooFinancialGateway
from forecast_provider_integration.schema import (
    REFRESH_POLICY,
    FailoverEvent,
    MarketSnapshot,
    utc_now,
)
from forecast_provider_integration.store import STORE

_GROWW = GrowwMarketGateway()
_YAHOO = YahooFinancialGateway()


def _age_sec(as_of: datetime | None) -> int:
    if not as_of:
        return 10**9
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    return max(0, int((utc_now() - as_of).total_seconds()))


def is_stale(snapshot: MarketSnapshot | None, *, max_age_sec: int | None = None) -> bool:
    policy = REFRESH_POLICY["groww_live_market"]
    limit = max_age_sec if max_age_sec is not None else int(policy["stale_after_sec"])
    if snapshot is None:
        return True
    age = _age_sec(snapshot.as_of)
    return age >= limit or bool(snapshot.stale)


def ensure_fresh_market_snapshot(
    entity: str,
    *,
    scope: str = "company",
    force: bool = False,
) -> dict[str, Any]:
    """Refresh Groww-primary snapshot only when stale. Yahoo only on Groww failure."""
    span = traces.begin(
        "forecast_market_snapshot",
        meta={"entity": entity, "scope": scope, "force": force},
    )
    key = entity.upper()
    existing = STORE.get_snapshot(key)
    policy = REFRESH_POLICY["groww_live_market"]

    if not force and existing and not is_stale(existing):
        age = _age_sec(existing.as_of)
        out = {
            "refreshed": False,
            "reason": "snapshot_fresh",
            "snapshot": existing.to_public_dict(),
            "age_sec": age,
            "stale_after_sec": policy["stale_after_sec"],
            "provider_called": None,
            "forecast_direct_provider_call": False,
        }
        traces.end(span, output=out)
        return out

    # Controlled refresh via Knowledge Platform gateway
    gspan = traces.begin("groww_market_refresh", meta={"entity": key})
    try:
        snap = _GROWW.fetch_snapshot(key, scope=scope)
        STORE.tick_collector("groww", ok=True, meta={"entity": key, "ltp": snap.ltp})
        traces.end(
            gspan,
            output={"provider": "groww", "ltp": snap.ltp, "websocket": snap.websocket},
        )
    except Exception as exc:
        traces.end(gspan, ok=False, output={"error": str(exc)})
        # Failover to Yahoo (only if Groww unavailable)
        fspan = traces.begin(
            "provider_failover",
            meta={"from": "groww", "to": "yahoo", "entity": key},
        )
        tip = _YAHOO.fallback_snapshot_fields(key)
        STORE.record_failover(
            FailoverEvent(
                from_provider="groww",
                to_provider="yahoo",
                reason=str(exc)[:200],
                entity=key,
            )
        )
        STORE.tick_collector("groww", ok=False, meta={"error": str(exc)[:120]})
        snap = MarketSnapshot(
            entity=key,
            scope=scope,
            ltp=tip.get("ltp"),
            change_pct=tip.get("change_pct"),
            source_provider="yahoo",
            fallback_used=True,
            stale=True,
            note=str(tip.get("note") or "Yahoo failover"),
        )
        # If yahoo also has no LTP, keep prior snapshot if any
        if snap.ltp is None and existing and existing.ltp is not None:
            snap = existing.model_copy(
                update={
                    "fallback_used": True,
                    "source_provider": existing.source_provider,
                    "note": "Retained prior AGI snapshot after Groww failure; Yahoo LTP unavailable",
                    "stale": is_stale(existing),
                }
            )
        traces.end(
            fspan,
            output={"failover": True, "to": "yahoo", "retained_prior": snap.ltp is not None},
        )

    published = STORE.publish_snapshot(snap)
    kspan = traces.begin("knowledge_refresh", meta={"entity": key, "kind": "market_snapshot"})
    traces.end(
        kspan,
        output={
            "snapshot_id": published.snapshot_id,
            "provider": published.source_provider,
            "freshness_sec": 0,
        },
    )

    out = {
        "refreshed": True,
        "reason": "stale_or_missing" if not force else "forced",
        "snapshot": published.to_public_dict(),
        "age_sec": 0,
        "stale_after_sec": policy["stale_after_sec"],
        "provider_called": published.source_provider,
        "fallback_used": published.fallback_used,
        "forecast_direct_provider_call": False,
        "gateway": "knowledge_platform_market_snapshot",
    }
    traces.end(span, output={"refreshed": True, "provider": published.source_provider})
    return out
