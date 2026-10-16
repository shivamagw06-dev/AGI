"""HMIP production facade."""

from __future__ import annotations

from typing import Any

from historical_macro_intelligence.engine import HistoricalMacroIntelligenceEngine

_ENGINE = HistoricalMacroIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, sources: list[str] | None = None) -> dict[str, Any]:
    return _ENGINE.run(sources=sources)


def history(*, limit: int = 200, country: str | None = None) -> dict[str, Any]:
    return _ENGINE.history(limit=limit, country=country)


def indicator(name: str, *, country: str = "India") -> dict[str, Any]:
    return _ENGINE.indicator(name, country=country)


def country(name: str, *, limit: int = 300) -> dict[str, Any]:
    return _ENGINE.country(name, limit=limit)


def timeline(*, indicator: str | None = None, country: str = "India") -> dict[str, Any]:
    return _ENGINE.timeline(indicator=indicator, country=country)


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    country: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return _ENGINE.search(
        q=q, category=category, country=country, namespace=namespace, limit=limit
    )
