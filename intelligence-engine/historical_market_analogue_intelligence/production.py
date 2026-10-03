"""HMKAI production facade."""

from __future__ import annotations

from typing import Any

from historical_market_analogue_intelligence.engine import (
    HistoricalMarketAnalogueIntelligenceEngine,
)

_ENGINE = HistoricalMarketAnalogueIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(
    *,
    market: str | None = None,
    enrich_hmkip: bool = True,
    enrich_cmktp: bool = True,
    top_k: int = 10,
) -> dict[str, Any]:
    return _ENGINE.run(
        market=market,
        enrich_hmkip=enrich_hmkip,
        enrich_cmktp=enrich_cmktp,
        top_k=top_k,
    )


def analogues(*, market: str | None = None, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues(market=market, limit=limit)


def analogues_for_market(market: str, *, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.analogues_for_market(market, limit=limit)


def search(
    *,
    market: str | None = None,
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    return _ENGINE.search(
        market=market,
        question=question,
        target_period=target_period,
        top_k=top_k,
        min_score=min_score,
        persist=False,
    )


def current_regime(*, market: str = "India") -> dict[str, Any]:
    return _ENGINE.current_regime(market=market)


def regime_history(*, market: str = "India", limit: int = 50) -> dict[str, Any]:
    return _ENGINE.regime_history(market=market, limit=limit)


def report(*, market: str = "India", top_k: int = 5) -> dict[str, Any]:
    return _ENGINE.report(market=market, top_k=top_k)


def forecast_tip(*, market: str = "India", top_k: int = 5) -> dict[str, Any]:
    return _ENGINE.forecast_tip(market=market, top_k=top_k)
