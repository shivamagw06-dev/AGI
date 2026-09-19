"""MKFI production facade."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence.engine import MarketForecastIntelligenceEngine

_ENGINE = MarketForecastIntelligenceEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(
    *,
    market: str | None = None,
    horizon: str | None = None,
    country: str | None = None,
    markets: list[str] | None = None,
    horizons: list[str] | None = None,
) -> dict[str, Any]:
    return _ENGINE.run(
        market=market,
        horizon=horizon,
        country=country,
        markets=markets,
        horizons=horizons,
    )


def forecast(*, market: str = "India", horizon: str = "6 Months") -> dict[str, Any]:
    return _ENGINE.forecast(market=market, horizon=horizon)


def forecast_all(*, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.forecast_all(limit=limit)


def scenarios(*, market: str = "India", horizon: str = "6 Months") -> dict[str, Any]:
    return _ENGINE.scenarios(market=market, horizon=horizon)


def probability(*, market: str = "India", horizon: str = "6 Months") -> dict[str, Any]:
    return _ENGINE.probability(market=market, horizon=horizon)


def catalysts(*, market: str = "India", horizon: str = "6 Months") -> dict[str, Any]:
    return _ENGINE.catalysts(market=market, horizon=horizon)


def risks(*, market: str = "India", horizon: str = "6 Months") -> dict[str, Any]:
    return _ENGINE.risks(market=market, horizon=horizon)


def report(
    *,
    market: str = "India",
    horizon: str = "6 Months",
    persist: bool = False,
) -> dict[str, Any]:
    return _ENGINE.report(market=market, horizon=horizon, persist=persist)


def history(
    *,
    market: str | None = None,
    horizon: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return _ENGINE.history(market=market, horizon=horizon, limit=limit)
