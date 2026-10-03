"""CMKP production facade."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.engine import ContinuousMacroKnowledgeEngine

_ENGINE = ContinuousMacroKnowledgeEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, sources: list[str] | None = None) -> dict[str, Any]:
    """Scheduler / ops only — not Ask."""
    return _ENGINE.run(sources=sources)


def india(*, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.india(limit=limit)


def global_macro(*, limit: int = 100) -> dict[str, Any]:
    return _ENGINE.global_macro(limit=limit)


def indicator(name: str, *, country: str | None = None) -> dict[str, Any]:
    return _ENGINE.indicator(name, country=country)


def releases(*, limit: int = 50) -> dict[str, Any]:
    return _ENGINE.releases(limit=limit)


def release_calendar(*, limit: int = 50) -> dict[str, Any]:
    return _ENGINE.release_calendar(limit=limit)
