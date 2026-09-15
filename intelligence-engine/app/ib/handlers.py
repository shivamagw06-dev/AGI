"""Soft default subscribers — never hard-depend on engines; never raise into bus."""

from __future__ import annotations

from typing import Any, Callable

from app.ib.config import CACHE_INVALIDATION_EVENTS
from app.ib.models import BusEvent, Subscription
from app.ib.store import IbStore


def _soft(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def build_default_handlers(
    store: IbStore,
    *,
    engines: dict[str, Any],
    cache_invalidate: bool = True,
) -> dict[str, Callable[[BusEvent, Subscription], Any]]:
    """Configuration-driven soft handlers for AOI/EVE/IIE/FLE/MEE/CAE."""

    def _symbol(event: BusEvent) -> str:
        p = event.payload or {}
        return str(p.get("company_symbol") or p.get("symbol") or event.aggregate_id or "").upper()

    def _invalidate(event: BusEvent, scopes: list[str]) -> None:
        if not cache_invalidate:
            return
        cae = engines.get("cae")
        if cae and hasattr(cae, "cache"):
            _soft(cae.cache, action="clear")
        store.cache_invalidation_log.append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "scopes": scopes,
                "producer": event.producer,
            }
        )
        store.cache_invalidation_log = store.cache_invalidation_log[-500:]
        store.metrics.cache_invalidations += 1

    def on_eve(event: BusEvent, _sub: Subscription) -> None:
        # Soft react to acquisition / company updates — never required for EVE to work.
        if event.event_type in ("DocumentDiscovered", "DocumentParsed", "CompanyUpdated"):
            eve = engines.get("eve")
            if eve and hasattr(eve, "consult") and _symbol(event):
                _soft(eve.consult, _symbol(event), limit=3)

    def on_iie(event: BusEvent, _sub: Subscription) -> None:
        sym = _symbol(event)
        iie = engines.get("iie")
        if event.event_type in ("EvidenceVerified", "CompanyUpdated", "KnowledgePublished") and iie and sym:
            if hasattr(iie, "analyse"):
                _soft(iie.analyse, sym)
            elif hasattr(iie, "consult"):
                _soft(iie.consult, sym, limit=3)

    def on_fle(event: BusEvent, _sub: Subscription) -> None:
        sym = _symbol(event)
        fle = engines.get("fle")
        if event.event_type in ("InvestmentThesisUpdated", "EvidenceVerified") and fle and sym:
            if hasattr(fle, "generate"):
                _soft(fle.generate, sym)
            elif hasattr(fle, "consult"):
                _soft(fle.consult, sym, limit=3)

    def on_mee(event: BusEvent, _sub: Subscription) -> None:
        mee = engines.get("mee")
        if event.event_type in ("ForecastUpdated", "CatalystDetected") and mee and hasattr(mee, "consult"):
            q = _symbol(event) or str((event.payload or {}).get("event_title") or "")
            if q:
                _soft(mee.consult, q, limit=3)

    def on_cae(event: BusEvent, _sub: Subscription) -> None:
        # Central cache invalidation driven by bus events (not polling).
        if event.event_type in CACHE_INVALIDATION_EVENTS or event.event_type == "CacheInvalidated":
            scopes = list((event.payload or {}).get("scopes") or ["cae", "company", "sector", "forecast", "events"])
            _invalidate(event, scopes)

    def on_aoi(event: BusEvent, _sub: Subscription) -> None:
        # AOI primarily publishes; soft acknowledge system health / connector events.
        if event.event_type in ("HealthChanged", "ConnectorFailed"):
            return

    def on_notifications(event: BusEvent, _sub: Subscription) -> None:
        # Future notification sink — record only in v1.
        store.cache_invalidation_log.append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "scopes": ["notification"],
                "producer": event.producer,
                "note": "notification_sink_v1_ack",
            }
        )

    return {
        "aoi": on_aoi,
        "eve": on_eve,
        "iie": on_iie,
        "fle": on_fle,
        "mee": on_mee,
        "cae": on_cae,
        "notifications": on_notifications,
    }


def default_subscriptions() -> list[dict[str, Any]]:
    """Declarative subscription catalogue — no hardcoded publisher routing."""
    return [
        {
            "subscriber": "eve",
            "event_types": ["DocumentDiscovered", "DocumentParsed", "CompanyUpdated", "EvidenceVerified"],
            "priority": "high",
        },
        {
            "subscriber": "iie",
            "event_types": [
                "EvidenceVerified",
                "CompanyUpdated",
                "KnowledgePublished",
                "InvestmentThesisUpdated",
            ],
            "priority": "high",
        },
        {
            "subscriber": "fle",
            "event_types": ["InvestmentThesisUpdated", "EvidenceVerified", "ForecastUpdated"],
            "priority": "normal",
        },
        {
            "subscriber": "mee",
            "event_types": ["ForecastUpdated", "CatalystDetected", "CorporateEventDetected"],
            "priority": "normal",
        },
        {
            "subscriber": "cae",
            "event_types": sorted(CACHE_INVALIDATION_EVENTS),
            "priority": "high",
        },
        {
            "subscriber": "aoi",
            "event_types": ["HealthChanged", "ConnectorFailed", "RetryScheduled"],
            "priority": "low",
        },
        {
            "subscriber": "notifications",
            "categories": ["notification", "market_event", "risk"],
            "priority": "normal",
        },
    ]
