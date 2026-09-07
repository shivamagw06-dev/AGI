"""Knowledge Retrieval Gateway for Macro — store only; never collects.

Ask / Research / Forecast must use this gateway (or /v1/macro/* read APIs).
"""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.store import STORE


def retrieve_india(*, limit: int = 100) -> dict[str, Any]:
    rows = STORE.published(limit=limit, country="India")
    return _bundle("India", rows)


def retrieve_global(*, limit: int = 100) -> dict[str, Any]:
    rows = [r for r in STORE.published(limit=500) if r.country != "India"]
    return _bundle("Global", rows[:limit])


def retrieve_indicator(indicator: str, *, country: str | None = None) -> dict[str, Any]:
    if country:
        latest = STORE.latest(indicator, country=country)
        versions = STORE.versions(indicator, country=country)
    else:
        # Prefer India, then any
        latest = STORE.latest(indicator, country="India") or STORE.latest(indicator, country="United States")
        if latest is None:
            for m in STORE.list_all(limit=500):
                if m.indicator.lower() == indicator.lower() and m.published:
                    latest = m
                    break
        versions = STORE.versions(indicator, country=latest.country) if latest else []

    if not latest:
        return {
            "found": False,
            "indicator": indicator,
            "collected_on_request": False,
            "reason": "not_published_in_macro_knowledge_store",
        }
    return {
        "found": True,
        "indicator": indicator,
        "latest": latest.to_public_dict(),
        "versions": [v.to_public_dict() for v in versions],
        "collected_on_request": False,
        "gateway": "CMKP_KRIG",
    }


def retrieve_releases(*, limit: int = 50) -> dict[str, Any]:
    rows = STORE.published(limit=limit)
    return {
        "n": len(rows),
        "releases": [r.to_public_dict() for r in rows],
        "collected_on_request": False,
        "gateway": "CMKP_KRIG",
    }


def _bundle(label: str, rows: list) -> dict[str, Any]:
    by_category: dict[str, list] = {}
    for r in rows:
        by_category.setdefault(r.category, []).append(r.to_public_dict())
    return {
        "region": label,
        "n": len(rows),
        "by_category": by_category,
        "indicators": [r.to_public_dict() for r in rows],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "gateway": "CMKP_KRIG",
        "freshness": {
            "rule": "consume_published_only",
            "stale_triggers_background_collector_not_ask": True,
        },
    }
