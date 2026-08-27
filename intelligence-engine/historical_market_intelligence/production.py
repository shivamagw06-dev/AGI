"""HMKIP production facade."""

from __future__ import annotations

from typing import Any

from historical_market_intelligence.engine import HistoricalMarketIntelligenceEngine

_ENGINE = HistoricalMarketIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(
    *, sources: list[str] | None = None, markets: list[str] | None = None
) -> dict[str, Any]:
    return _ENGINE.run(sources=sources, markets=markets)


def history(*, limit: int = 200, market: str | None = None) -> dict[str, Any]:
    return _ENGINE.history(limit=limit, market=market)


def market(name: str, *, limit: int = 300) -> dict[str, Any]:
    return _ENGINE.market(name, limit=limit)


def timeline(
    *, market: str | None = None, indicator: str | None = None
) -> dict[str, Any]:
    return _ENGINE.timeline(market=market, indicator=indicator)


def regimes(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.regimes(market=market, limit=limit)


def breadth(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.breadth(market=market, limit=limit)


def liquidity(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.liquidity(market=market, limit=limit)


def volatility(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.volatility(market=market, limit=limit)


def flows(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.flows(market=market, limit=limit)


def search(
    *,
    q: str | None = None,
    category: str | None = None,
    market: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return _ENGINE.search(
        q=q, category=category, market=market, namespace=namespace, limit=limit
    )
