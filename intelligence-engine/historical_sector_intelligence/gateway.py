"""Read-only Historical Sector KRIG — never collects."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import canonicalize
from historical_sector_intelligence import traces
from historical_sector_intelligence.store import STORE


def retrieve_history(*, limit: int = 200, sector_key: str | None = None) -> dict[str, Any]:
    span = traces.begin("historical_sector_retrieval", meta={"scope": "history", "sector": sector_key})
    key = canonicalize(sector_key) if sector_key else None
    rows = STORE.list_all(limit=limit, sector_key=key)
    out = {
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "coverage": STORE.coverage(),
        "providers_queried": [],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "gateway": "HSIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_sector(sector: str, *, limit: int = 300) -> dict[str, Any]:
    key = canonicalize(sector) or sector.lower().replace(" ", "_")
    span = traces.begin("historical_sector_retrieval", meta={"scope": "sector", "sector": key})
    rows = STORE.list_all(limit=limit, sector_key=key)
    tl = STORE.get_timeline(key, indicator="Revenue Growth")
    pe_tl = STORE.get_timeline(key, indicator="Average PE")
    out = {
        "found": bool(rows),
        "sector": key,
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "timeline": tl.to_public_dict() if tl else None,
        "valuation_timeline": pe_tl.to_public_dict() if pe_tl else None,
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HSIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"found": out["found"], "n": out["n"]})
    return out


def retrieve_timeline(*, sector: str | None = None, indicator: str | None = None) -> dict[str, Any]:
    span = traces.begin(
        "historical_sector_retrieval",
        meta={"scope": "timeline", "sector": sector, "indicator": indicator},
    )
    key = canonicalize(sector) if sector else None
    if key and indicator:
        tl = STORE.get_timeline(key, indicator=indicator)
        timelines = [tl] if tl else []
    elif key:
        timelines = STORE.list_timelines(sector_key=key, limit=50)
    else:
        timelines = STORE.list_timelines(limit=100)
    out = {
        "n": len(timelines),
        "timelines": [t.to_public_dict() for t in timelines],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HSIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_events(*, sector: str | None = None, limit: int = 100) -> dict[str, Any]:
    span = traces.begin("historical_sector_retrieval", meta={"scope": "events", "sector": sector})
    key = canonicalize(sector) if sector else None
    rows = STORE.list_all(limit=1000, sector_key=key, category="Events")
    # Also include Key Event indicator
    if not rows:
        rows = [
            r
            for r in STORE.list_all(limit=1000, sector_key=key)
            if r.indicator == "Key Event" or r.key_events
        ]
    else:
        extra = [
            r
            for r in STORE.list_all(limit=1000, sector_key=key)
            if r.indicator == "Key Event" and r.hsko_id not in {x.hsko_id for x in rows}
        ]
        rows = rows + extra
    rows = rows[:limit]
    out = {
        "n": len(rows),
        "events": [
            {
                "sector_key": r.sector_key,
                "sector_label": r.sector_label,
                "period": r.period,
                "events": r.key_events,
                "policies": r.government_policies,
                "macro_regime": r.macro_regime,
                "leader": r.sector_leader,
                "namespace": r.namespace,
            }
            for r in rows
        ],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HSIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    sector: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    span = traces.begin("historical_sector_retrieval", meta={"scope": "search", "q": q})
    key = canonicalize(sector) if sector else None
    rows = STORE.list_all(limit=2000, sector_key=key, category=category, namespace=namespace)
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in r.sector_key
            or ql in r.sector_label.lower()
            or ql in r.indicator.lower()
            or ql in r.period.lower()
            or any(ql in e.lower() for e in r.key_events)
            or (r.macro_regime and ql in r.macro_regime.lower())
        ]
    rows = rows[:limit]
    out = {
        "q": q,
        "n": len(rows),
        "results": [r.to_public_dict() for r in rows],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HSIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out
