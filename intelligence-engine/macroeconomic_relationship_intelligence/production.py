"""MRI production facade."""

from __future__ import annotations

from typing import Any

from macroeconomic_relationship_intelligence.engine import (
    MacroeconomicRelationshipIntelligenceEngine,
)

_ENGINE = MacroeconomicRelationshipIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, enrich_hmip: bool = True) -> dict[str, Any]:
    return _ENGINE.run(enrich_hmip=enrich_hmip)


def relationships(*, limit: int = 200) -> dict[str, Any]:
    return _ENGINE.relationships(limit=limit)


def for_indicator(indicator: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_indicator(indicator, limit=limit)


def for_company(ticker: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_company(ticker, limit=limit)


def for_sector(sector: str, *, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.for_sector(sector, limit=limit)


def graph() -> dict[str, Any]:
    return _ENGINE.graph()
