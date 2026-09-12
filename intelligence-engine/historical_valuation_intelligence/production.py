"""API-facing HVIE surface."""

from __future__ import annotations

from typing import Any, Optional

from historical_valuation_intelligence import compute, engine, runtime
from historical_valuation_intelligence.models import ENGINE_CODE, VERSION


def health() -> dict[str, Any]:
    rt = runtime.status()
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "role": "continuous_historical_valuation_service",
        "vendor_historical_ratios": False,
        "reconstruction": "prices + normalized financial statements + corporate actions + VPAE",
        "reconstruction_version": "8.3B",
        "statement_priority": ["quarterly_TTM", "annual", "skip"],
        "statement_type_preference": "CONSOLIDATED",
        "windows": ["1y", "3y", "5y", "10y", "15y", "20y", "max"],
        "gates": ["valuation_policy", "dqiv"],
        "runtime": rt.get("runtime"),
        "coverage_pct": rt.get("coverage_pct"),
        "seeded": rt.get("seeded"),
        "universe": rt.get("universe"),
        "schedules": rt.get("schedules"),
        "endpoints": [
            "/v1/hvie/company/{symbol}",
            "/v1/hvie/history/{symbol}",
            "/v1/hvie/statistics/{symbol}",
            "/v1/hvie/percentiles/{symbol}",
            "/v1/hvie/bands/{symbol}",
            "/v1/hvie/regimes/{symbol}",
            "/v1/hvie/rerating/{symbol}",
            "/v1/hvie/coverage/{symbol}",
            "/v1/historical-valuation/health",
            "/v1/historical-valuation/company/{symbol}",
            "/v1/historical-valuation/history/{symbol}",
            "/v1/historical-valuation/statistics/{symbol}",
            "/v1/historical-valuation/bands/{symbol}",
            "/v1/historical-valuation/percentiles/{symbol}",
            "/v1/historical-valuation/regimes/{symbol}",
            "/v1/historical-valuation/rerating/{symbol}",
            "/v1/historical-valuation/coverage/{symbol}",
            "/v1/historical-valuation/coverage-dashboard",
            "/v1/historical-valuation/reconstruct/{symbol}",
            "/v1/historical-valuation/runtime/{status,run,start,stop}",
        ],
    }


def company(symbol: str, *, metric: Optional[str] = None, window: str = "10y") -> dict[str, Any]:
    return engine.company_pack(symbol, metric=metric, window=window)


def history(
    symbol: str,
    *,
    metric: Optional[str] = None,
    window: str = "max",
    limit: int = 5000,
) -> dict[str, Any]:
    return engine.history_for(symbol, metric=metric, window=window, limit=limit)


def statistics(
    symbol: str,
    *,
    metric: str = "pe",
    window: Optional[str] = None,
) -> dict[str, Any]:
    return engine.statistics_for(symbol, metric=metric, window=window)


def bands(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    return engine.bands_for(symbol, metric=metric, window=window)


def percentiles(symbol: str, *, metric: str = "pe") -> dict[str, Any]:
    return engine.percentiles_for(symbol, metric=metric)


def regimes(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    return engine.regimes_for(symbol, metric=metric, window=window)


def rerating(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    return engine.rerating_for(symbol, metric=metric, window=window)


def coverage(symbol: str, *, metric: Optional[str] = None) -> dict[str, Any]:
    return engine.coverage_for(symbol, metric=metric)


def reconstruct(
    symbol: str,
    *,
    cadence: str = "daily",
    start: Optional[str] = None,
    end: Optional[str] = None,
    incremental: bool = False,
) -> dict[str, Any]:
    if incremental:
        return compute.incremental_price_update(symbol)
    return compute.reconstruct(symbol, cadence=cadence, start=start, end=end)


def runtime_status() -> dict[str, Any]:
    return runtime.status()


def runtime_run(mode: str = "auto", **kwargs: Any) -> dict[str, Any]:
    return runtime.run_once(mode, **kwargs)


def runtime_start() -> dict[str, Any]:
    return runtime.start_loop()


def runtime_stop() -> dict[str, Any]:
    return runtime.stop_loop()


def coverage_dashboard(*, limit: int = 200) -> dict[str, Any]:
    return runtime.coverage_dashboard(limit=limit)
