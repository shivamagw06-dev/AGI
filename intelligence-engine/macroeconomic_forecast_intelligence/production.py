"""MFI production facade."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence.engine import (
    MacroeconomicForecastIntelligenceEngine,
)

_ENGINE = MacroeconomicForecastIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, country: str = "India", region: str = "India") -> dict[str, Any]:
    return _ENGINE.run(country=country, region=region)


def forecast(*, country: str = "India", region: str | None = None) -> dict[str, Any]:
    return _ENGINE.forecast(country=country, region=region)


def india() -> dict[str, Any]:
    return _ENGINE.india()


def global_forecast() -> dict[str, Any]:
    return _ENGINE.global_forecast()


def scenarios(*, country: str = "India") -> dict[str, Any]:
    return _ENGINE.scenarios(country=country)


def probability(*, country: str = "India") -> dict[str, Any]:
    return _ENGINE.probability(country=country)


def report(*, country: str = "India", persist: bool = False) -> dict[str, Any]:
    return _ENGINE.report(country=country, persist=persist)


def history(*, country: str = "India", limit: int = 20) -> dict[str, Any]:
    return _ENGINE.history(country=country, limit=limit)
