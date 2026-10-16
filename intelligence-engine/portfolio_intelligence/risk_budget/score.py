"""Risk budget — volatility / drawdown / risk contribution proxies."""

from __future__ import annotations

import math
from typing import Any

# Sector vol priors (annualised approx)
_SECTOR_VOL = {
    "banks": 0.22,
    "it_services": 0.20,
    "fmcg": 0.16,
    "telecom": 0.28,
    "consumer_internet": 0.38,
    "energy_conglomerate": 0.24,
    "other": 0.25,
}


def risk_budget(
    holdings: list[dict[str, Any]],
    *,
    max_drawdown: float,
    avg_corr: float,
) -> dict[str, Any]:
    # Simple variance proxy: w'Σw with sector vols + avg corr
    contrib = []
    var = 0.0
    for h in holdings:
        w = float(h.get("weight") or 0)
        vol = _SECTOR_VOL.get(str(h.get("sector") or "other"), 0.25)
        # marginal risk contribution proxy
        mrc = w * vol * (0.5 + 0.5 * avg_corr)
        var += (w * vol) ** 2
        contrib.append(
            {
                "ticker": h.get("ticker"),
                "weight": round(w, 4),
                "vol_prior": vol,
                "risk_contribution_proxy": round(mrc, 4),
            }
        )
    # add cross terms roughly
    port_vol = (var + avg_corr * 0.02) ** 0.5
    port_vol = min(0.45, max(0.08, port_vol + avg_corr * 0.05))
    dd_usage = min(1.5, port_vol * 2.2 / max(0.05, float(max_drawdown or 0.25)))

    score = max(0.0, min(100.0, 100.0 - (port_vol - 0.12) * 250 - max(0.0, dd_usage - 1.0) * 40))
    return {
        "risk_score": round(score, 1),
        "expected_volatility": round(port_vol, 3),
        "downside_risk_proxy": round(port_vol * 1.15, 3),
        "max_drawdown_budget": max_drawdown,
        "drawdown_budget_usage": round(dd_usage, 3),
        "contributions": sorted(contrib, key=lambda c: -c["risk_contribution_proxy"])[:10],
        "stress_concentration": "elevated" if dd_usage > 1.1 else "within_budget",
        "method": "sector_volatility_prior_v1",
    }


def empirical_risk_budget(rows: list[dict[str, Any]], *, max_drawdown: float) -> dict[str, Any] | None:
    """Calculate portfolio risk from dated realized returns; percentages are converted to decimals."""
    pairs = []
    for row in rows:
        try:
            portfolio_return = float(row.get("return_pct")) / 100.0
        except (TypeError, ValueError):
            continue
        benchmark = row.get("benchmark_return_pct")
        try:
            benchmark_return = float(benchmark) / 100.0 if benchmark is not None else None
        except (TypeError, ValueError):
            benchmark_return = None
        pairs.append((portfolio_return, benchmark_return))
    if len(pairs) < 63:
        return None
    values = [row[0] for row in pairs]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
    volatility = math.sqrt(variance) * math.sqrt(252)
    wealth = peak = 1.0
    drawdown = 0.0
    for value in values:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    comparable = [(p, b) for p, b in pairs if b is not None]
    beta = tracking_error = None
    if len(comparable) >= 63:
        p_values = [row[0] for row in comparable]
        b_values = [row[1] for row in comparable]
        p_mean = sum(p_values) / len(p_values)
        b_mean = sum(b_values) / len(b_values)
        covariance = sum((p - p_mean) * (b - b_mean) for p, b in comparable) / max(1, len(comparable) - 1)
        benchmark_variance = sum((b - b_mean) ** 2 for b in b_values) / max(1, len(b_values) - 1)
        beta = covariance / benchmark_variance if benchmark_variance > 1e-12 else None
        active = [p - b for p, b in comparable]
        active_mean = sum(active) / len(active)
        active_variance = sum((value - active_mean) ** 2 for value in active) / max(1, len(active) - 1)
        tracking_error = math.sqrt(active_variance) * math.sqrt(252)
    budget = max(0.01, float(max_drawdown or 0.25))
    usage = abs(drawdown) / budget
    return {
        "risk_score": round(max(0.0, min(100.0, 100.0 - volatility * 150 - max(0.0, usage - 1.0) * 40)), 1),
        "expected_volatility": round(volatility, 4),
        "downside_risk_proxy": round(abs(drawdown), 4),
        "realized_max_drawdown": round(drawdown, 4),
        "max_drawdown_budget": budget,
        "drawdown_budget_usage": round(usage, 4),
        "beta_to_benchmark": round(beta, 4) if beta is not None else None,
        "tracking_error": round(tracking_error, 4) if tracking_error is not None else None,
        "observations": len(values),
        "benchmark_observations": len(comparable),
        "contributions": [],
        "stress_concentration": "breach" if usage > 1.0 else "within_budget",
        "method": "empirical_daily_returns_v1",
    }
