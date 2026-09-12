"""HSIP production facade."""

from __future__ import annotations

from typing import Any

from historical_sector_intelligence.engine import HistoricalSectorIntelligenceEngine

_ENGINE = HistoricalSectorIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, sources: list[str] | None = None) -> dict[str, Any]:
    return _ENGINE.run(sources=sources)


def history(*, limit: int = 200, sector: str | None = None) -> dict[str, Any]:
    return _ENGINE.history(limit=limit, sector=sector)


def sector(name: str, *, limit: int = 300) -> dict[str, Any]:
    return _ENGINE.sector(name, limit=limit)


def timeline(*, sector: str | None = None, indicator: str | None = None) -> dict[str, Any]:
    return _ENGINE.timeline(sector=sector, indicator=indicator)


def events(*, sector: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.events(sector=sector, limit=limit)


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    sector: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return _ENGINE.search(
        q=q, category=category, sector=sector, namespace=namespace, limit=limit
    )
