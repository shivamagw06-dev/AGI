"""HSAI production facade."""

from __future__ import annotations

from typing import Any

from historical_sector_analogue_intelligence.engine import (
    HistoricalSectorAnalogueIntelligenceEngine,
)

_ENGINE = HistoricalSectorAnalogueIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(
    *,
    sector: str | None = None,
    enrich_hsip: bool = True,
    enrich_cskp: bool = True,
    top_k: int = 10,
) -> dict[str, Any]:
    return _ENGINE.run(
        sector=sector,
        enrich_hsip=enrich_hsip,
        enrich_cskp=enrich_cskp,
        top_k=top_k,
    )


def analogues(*, sector: str | None = None, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues(sector=sector, limit=limit)


def analogues_for_sector(sector: str, *, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues_for_sector(sector, limit=limit)


def search(
    *,
    sector: str | None = None,
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    return _ENGINE.search(
        sector=sector,
        question=question,
        target_period=target_period,
        top_k=top_k,
        min_score=min_score,
        persist=False,
    )


def current_regime(*, sector: str = "Banking") -> dict[str, Any]:
    return _ENGINE.current_regime(sector=sector)


def regime_history(*, sector: str = "Banking", limit: int = 50) -> dict[str, Any]:
    return _ENGINE.regime_history(sector=sector, limit=limit)


def forecast_tip(*, sector: str = "Banking", top_k: int = 5) -> dict[str, Any]:
    return _ENGINE.forecast_tip(sector=sector, top_k=top_k)
