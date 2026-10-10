"""HMAI production facade."""

from __future__ import annotations

from typing import Any

from historical_macro_analogue_intelligence.engine import (
    HistoricalMacroAnalogueIntelligenceEngine,
)

_ENGINE = HistoricalMacroAnalogueIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, country: str = "India", enrich_hmip: bool = True, top_k: int = 10) -> dict[str, Any]:
    return _ENGINE.run(country=country, enrich_hmip=enrich_hmip, top_k=top_k)


def analogues(*, country: str | None = None, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues(country=country, limit=limit)


def analogues_for_country(country: str, *, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues_for_country(country, limit=limit)


def search(
    *,
    country: str = "India",
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    return _ENGINE.search(
        country=country,
        question=question,
        target_period=target_period,
        top_k=top_k,
        min_score=min_score,
        persist=False,
    )


def current_regime(*, country: str = "India") -> dict[str, Any]:
    return _ENGINE.current_regime(country=country)


def regime_history(*, country: str = "India", limit: int = 50) -> dict[str, Any]:
    return _ENGINE.regime_history(country=country, limit=limit)


def forecast_tip(*, country: str = "India", top_k: int = 5) -> dict[str, Any]:
    return _ENGINE.forecast_tip(country=country, top_k=top_k)
