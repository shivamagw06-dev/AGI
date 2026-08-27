"""SFI production facade."""

from __future__ import annotations

from typing import Any

from sector_forecast_intelligence.engine import SectorForecastIntelligenceEngine

_ENGINE = SectorForecastIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, sector: str | None = None, country: str = "India") -> dict[str, Any]:
    return _ENGINE.run(sector=sector, country=country)


def forecast(*, sector: str = "Banking") -> dict[str, Any]:
    return _ENGINE.forecast(sector=sector)


def forecast_all(*, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.forecast_all(limit=limit)


def scenarios(*, sector: str = "Banking") -> dict[str, Any]:
    return _ENGINE.scenarios(sector=sector)


def probability(*, sector: str = "Banking") -> dict[str, Any]:
    return _ENGINE.probability(sector=sector)


def report(*, sector: str = "Banking", persist: bool = False) -> dict[str, Any]:
    return _ENGINE.report(sector=sector, persist=persist)


def history(*, sector: str | None = None, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.history(sector=sector, limit=limit)
