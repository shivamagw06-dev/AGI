"""Derive risk metrics from primitive return series.

Produces risk_drivers and downside fields for institutional evidence packs
and IPI Risk Intelligence. Formulas are explicit and auditable.
"""

from __future__ import annotations

import math
from typing import Any

from .market_series import risk_primitives


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _covariance(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx, my = _mean(xs[:n]), _mean(ys[:n])
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / (n - 1)


def _percentile(sorted_xs: list[float], p: float) -> float:
    if not sorted_xs:
        return 0.0
    if p <= 0:
        return sorted_xs[0]
    if p >= 100:
        return sorted_xs[-1]
    k = (len(sorted_xs) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_xs[int(k)]
    return sorted_xs[f] * (c - k) + sorted_xs[c] * (k - f)


def derive_risk_metrics(ticker: str) -> dict[str, Any] | None:
    prim = risk_primitives(ticker)
    if not prim:
        return None

    rets = prim["monthly_returns"]
    bench = prim["benchmark_returns"]
    n = min(len(rets), len(bench))
    rets, bench = rets[:n], bench[:n]

    vol_m = _stdev(rets)
    vol_ann = vol_m * math.sqrt(12)
    bench_vol = _stdev(bench) * math.sqrt(12)
    cov = _covariance(rets, bench)
    bench_var = _stdev(bench) ** 2
    beta = (cov / bench_var) if bench_var > 1e-12 else 0.0
    corr = (cov / (_stdev(rets) * _stdev(bench))) if _stdev(rets) > 1e-12 and _stdev(bench) > 1e-12 else 0.0

    # Historical simulation VaR / ES on monthly returns (loss = -return)
    losses = sorted(-r for r in rets)
    var_95 = _percentile(losses, 95)
    var_99 = _percentile(losses, 99)
    # Expected shortfall: mean of losses beyond VaR95
    beyond = [l for l in losses if l >= var_95]
    es_95 = _mean(beyond) if beyond else var_95

    # Downside deviation (semi-deviation vs 0)
    neg = [r for r in rets if r < 0]
    downside_dev = _stdev(neg) * math.sqrt(12) if len(neg) >= 2 else abs(_mean(neg)) * math.sqrt(12) if neg else 0.0
    max_dd = 0.0
    peak = 0.0
    wealth = 0.0
    for r in rets:
        wealth += r
        peak = max(peak, wealth)
        max_dd = max(max_dd, peak - wealth)

    # Simple factor tilt proxy from beta + idiosyncratic vol
    idio_vol = max(0.0, vol_ann - abs(beta) * bench_vol)
    liquidity_proxy = max(0.1, 1.0 - min(0.9, vol_ann / 80.0))  # higher vol → lower liquidity score

    risk_drivers = {
        "volatility_ann_pct": round(vol_ann, 4),
        "beta_vs_benchmark": round(beta, 4),
        "correlation_vs_benchmark": round(corr, 4),
        "idiosyncratic_vol_pct": round(idio_vol, 4),
        "factor_exposure": {
            "market_beta": round(beta, 4),
            "residual_vol_pct": round(idio_vol, 4),
        },
        "liquidity_score": round(liquidity_proxy, 4),
    }
    downside = {
        "var_95_monthly_pct": round(var_95, 4),
        "var_99_monthly_pct": round(var_99, 4),
        "expected_shortfall_95_pct": round(es_95, 4),
        "downside_deviation_ann_pct": round(downside_dev, 4),
        "max_drawdown_pct": round(max_dd, 4),
    }

    formulas = {
        "volatility_ann": "stdev(monthly_returns) * sqrt(12)",
        "beta": "cov(asset, benchmark) / var(benchmark)",
        "var_95": "historical_simulation_percentile(losses, 95)",
        "expected_shortfall_95": "mean(losses >= VaR95)",
        "downside_deviation": "stdev(negative_returns) * sqrt(12)",
    }

    return {
        "ticker": ticker.upper(),
        "provider": "derived_risk_producer",
        "data_class": "derived",
        "horizon_months": n,
        "risk_drivers": risk_drivers,
        "downside": downside,
        "formulas": formulas,
        "primitives_ref": "market_series.monthly_returns",
        "audit": {
            "method": "historical_simulation_from_monthly_returns",
            "benchmark": "synthetic_equity_benchmark",
            "reproducible": True,
        },
    }


def risk_field_payload(ticker: str, field: str) -> dict[str, Any] | None:
    """Return a single pack-ready field payload for risk_drivers or downside."""
    derived = derive_risk_metrics(ticker)
    if not derived or field not in ("risk_drivers", "downside"):
        return None
    return {
        "value": derived[field],
        "as_of": None,
        "provider": derived["provider"],
        "data_class": derived["data_class"],
        "confidence": 0.72,
        "formula": derived["formulas"],
        "audit": derived["audit"],
        "horizon_months": derived["horizon_months"],
    }
