"""Read-only Historical Market KRIG — never collects."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import canonicalize
from historical_market_intelligence import traces
from historical_market_intelligence.store import STORE


def retrieve_history(*, limit: int = 200, market_key: str | None = None) -> dict[str, Any]:
    span = traces.begin(
        "historical_market_retrieval", meta={"scope": "history", "market": market_key}
    )
    key = canonicalize(market_key) if market_key else None
    rows = STORE.list_all(limit=limit, market_key=key)
    out = {
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "coverage": STORE.coverage(),
        "providers_queried": [],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "gateway": "HMKIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_market(market: str, *, limit: int = 300) -> dict[str, Any]:
    key = canonicalize(market) or market.lower().replace(" ", "_")
    span = traces.begin(
        "historical_market_retrieval", meta={"scope": "market", "market": key}
    )
    rows = STORE.list_all(limit=limit, market_key=key)
    tl = STORE.get_timeline(key, indicator="Market Health")
    out = {
        "found": bool(rows),
        "market": key,
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "timeline": tl.to_public_dict() if tl else None,
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMKIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"found": out["found"], "n": out["n"]})
    return out


def retrieve_timeline(
    *, market: str | None = None, indicator: str | None = None
) -> dict[str, Any]:
    span = traces.begin(
        "historical_market_retrieval",
        meta={"scope": "timeline", "market": market, "indicator": indicator},
    )
    key = canonicalize(market) if market else None
    if key and indicator:
        tl = STORE.get_timeline(key, indicator=indicator)
        timelines = [tl] if tl else []
    elif key:
        timelines = STORE.list_timelines(market_key=key, limit=50)
    else:
        timelines = STORE.list_timelines(limit=100)
    out = {
        "n": len(timelines),
        "timelines": [t.to_public_dict() for t in timelines],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMKIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_by_category(
    category: str, *, market: str | None = None, limit: int = 100
) -> dict[str, Any]:
    span = traces.begin(
        "historical_market_retrieval",
        meta={"scope": category.lower(), "market": market},
    )
    key = canonicalize(market) if market else None
    rows = STORE.list_all(limit=limit, market_key=key, category=category)
    out = {
        "category": category,
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMKIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_regimes(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    span = traces.begin(
        "historical_market_retrieval", meta={"scope": "regimes", "market": market}
    )
    key = canonicalize(market) if market else None
    rows = [
        r
        for r in STORE.list_all(limit=2000, market_key=key)
        if r.category in {"Cycles", "Events"} or r.indicator == "Market Regime"
    ][:limit]
    out = {
        "n": len(rows),
        "regimes": [
            {
                "market_key": r.market_key,
                "market_label": r.market_label,
                "period": r.period,
                "market_regime": r.market_regime,
                "events": r.major_events,
                "value": r.value,
                "namespace": r.namespace,
            }
            for r in rows
        ],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMKIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    market: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    span = traces.begin("historical_market_retrieval", meta={"scope": "search", "q": q})
    key = canonicalize(market) if market else None
    rows = STORE.list_all(limit=2000, market_key=key, category=category, namespace=namespace)
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in r.market_key
            or ql in r.market_label.lower()
            or ql in r.indicator.lower()
            or ql in r.period.lower()
            or any(ql in e.lower() for e in r.major_events)
            or (r.market_regime and ql in r.market_regime.lower())
        ]
    rows = rows[:limit]
    out = {
        "q": q,
        "n": len(rows),
        "results": [r.to_public_dict() for r in rows],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMKIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out
