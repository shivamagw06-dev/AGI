"""CMKTP production facade."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.engine import ContinuousMarketKnowledgeEngine

_ENGINE = ContinuousMarketKnowledgeEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, domains: list[str] | None = None, trigger: str | None = None) -> dict[str, Any]:
    """Ops / event-driven only — not Ask."""
    return _ENGINE.run(domains=domains, trigger=trigger)


def markets(*, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.markets(limit=limit)


def market() -> dict[str, Any]:
    return _ENGINE.market()


def domain(name: str) -> dict[str, Any]:
    return _ENGINE.domain(name)


def regime() -> dict[str, Any]:
    return _ENGINE.regime()


def breadth() -> dict[str, Any]:
    return _ENGINE.breadth()


def liquidity() -> dict[str, Any]:
    return _ENGINE.liquidity()


def leadership() -> dict[str, Any]:
    return _ENGINE.leadership()


def flows() -> dict[str, Any]:
    return _ENGINE.flows()


def volatility() -> dict[str, Any]:
    return _ENGINE.volatility()


def market_health() -> dict[str, Any]:
    return _ENGINE.health_score()
