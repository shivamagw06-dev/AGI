"""Historical Macro Retrieval Gateway — store only; never collects or calls providers."""

from __future__ import annotations

from typing import Any

from historical_macro_intelligence import traces
from historical_macro_intelligence.store import STORE
from historical_macro_intelligence.timeline import build_timeline


def retrieve_history(*, limit: int = 200, country: str | None = None) -> dict[str, Any]:
    span = traces.begin("historical_macro_retrieval", meta={"scope": "all", "country": country})
    rows = STORE.list_all(limit=limit, country=country)
    out = {
        "n": len(rows),
        "observations": [r.to_public_dict() for r in rows],
        "coverage": STORE.coverage(),
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_indicator(indicator: str, *, country: str = "India") -> dict[str, Any]:
    span = traces.begin(
        "historical_macro_retrieval",
        meta={"scope": "indicator", "indicator": indicator, "country": country},
    )
    series = STORE.series(indicator, country=country)
    if not series:
        # Try other countries
        for c in ("United States", "Global"):
            series = STORE.series(indicator, country=c)
            if series:
                country = c
                break
    timeline = STORE.get_timeline(indicator, country=country)
    if series and not timeline:
        timeline = build_timeline(indicator, country=country)
    out = {
        "found": bool(series),
        "indicator": indicator,
        "country": country,
        "n": len(series),
        "series": [r.to_public_dict() for r in series],
        "timeline": timeline.to_public_dict() if timeline else None,
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMIP_KRIG",
        "immutable": True,
    }
    traces.end(span, output={"found": out["found"], "n": out["n"]})
    return out


def retrieve_country(country: str, *, limit: int = 300) -> dict[str, Any]:
    span = traces.begin("historical_macro_retrieval", meta={"scope": "country", "country": country})
    rows = STORE.list_all(limit=limit, country=country)
    by_indicator: dict[str, int] = {}
    for r in rows:
        by_indicator[r.indicator] = by_indicator.get(r.indicator, 0) + 1
    out = {
        "country": country,
        "n": len(rows),
        "by_indicator": by_indicator,
        "observations": [r.to_public_dict() for r in rows],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_timeline(
    *,
    indicator: str | None = None,
    country: str = "India",
) -> dict[str, Any]:
    span = traces.begin(
        "historical_macro_retrieval",
        meta={"scope": "timeline", "indicator": indicator},
    )
    if indicator:
        tl = STORE.get_timeline(indicator, country=country) or build_timeline(
            indicator, country=country
        )
        out = {
            "n": 1,
            "timelines": [tl.to_public_dict()],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMIP_KRIG",
        }
    else:
        rows = STORE.list_timelines(limit=100)
        out = {
            "n": len(rows),
            "timelines": [t.to_public_dict() for t in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMIP_KRIG",
        }
    traces.end(span, output={"n": out["n"]})
    return out


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    country: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    span = traces.begin("historical_macro_retrieval", meta={"scope": "search", "q": q})
    rows = STORE.list_all(limit=1000, country=country, category=category, namespace=namespace)
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in r.indicator.lower()
            or ql in r.category.lower()
            or ql in r.period.lower()
            or ql in r.source.lower()
        ]
    rows = rows[:limit]
    out = {
        "n": len(rows),
        "query": {"q": q, "category": category, "country": country, "namespace": namespace},
        "results": [r.to_public_dict() for r in rows],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "HMIP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out
