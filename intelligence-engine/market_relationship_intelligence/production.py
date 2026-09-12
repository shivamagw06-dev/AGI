"""MKRI production facade."""

from __future__ import annotations

from typing import Any

from market_relationship_intelligence.engine import MarketRelationshipIntelligenceEngine

_ENGINE = MarketRelationshipIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(
    *,
    enrich_hmkip: bool = True,
    enrich_hmip: bool = True,
    enrich_hsip: bool = True,
    enrich_macro_mri: bool = True,
) -> dict[str, Any]:
    return _ENGINE.run(
        enrich_hmkip=enrich_hmkip,
        enrich_hmip=enrich_hmip,
        enrich_hsip=enrich_hsip,
        enrich_macro_mri=enrich_macro_mri,
    )


def relationships(*, limit: int = 200) -> dict[str, Any]:
    return _ENGINE.relationships(limit=limit)


def for_indicator(indicator: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_indicator(indicator, limit=limit)


def for_sector(sector: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_sector(sector, limit=limit)


def for_company(ticker: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_company(ticker, limit=limit)


def search(
    *,
    q: str | None = None,
    kind: str | None = None,
    source: str | None = None,
    target: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return _ENGINE.search(q=q, kind=kind, source=source, target=target, limit=limit)


def graph(*, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    return _ENGINE.graph(start=start, end=end)
