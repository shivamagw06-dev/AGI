"""CSKP production facade."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.engine import ContinuousSectorKnowledgeEngine

_ENGINE = ContinuousSectorKnowledgeEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, sectors: list[str] | None = None, trigger: str | None = None) -> dict[str, Any]:
    """Ops / event-driven only — not Ask."""
    return _ENGINE.run(sectors=sectors, trigger=trigger)


def sectors(*, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.sectors(limit=limit)


def sector(name: str) -> dict[str, Any]:
    return _ENGINE.sector(name)


def leaders(*, limit: int = 50) -> dict[str, Any]:
    return _ENGINE.leaders(limit=limit)


def comparison(*, sectors: list[str] | None = None) -> dict[str, Any]:
    return _ENGINE.comparison(sectors=sectors)


def calendar(*, limit: int = 50) -> dict[str, Any]:
    return _ENGINE.calendar(limit=limit)
