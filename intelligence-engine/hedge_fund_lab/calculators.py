"""Strategy calculators — deterministic, server-side.

Sliders in the UI send inputs; every number comes back computed here, so the
arithmetic is identical for every consumer and auditable in one place.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def _num(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if out == out and abs(out) != float("inf") else default


# ---------------------------------------------------------------------------
# Capital allocation and exposure
# ---------------------------------------------------------------------------
def exposure(capital: Any, long_book: Any, short_book: Any) -> dict[str, Any]:
    """Gross, net and cash from a long/short book."""
    cap = _num(capital)
    long_v, short_v = _num(long_book), _num(short_book)
    if cap <= 0:
        return {"ok": False, "error": "capital_must_be_positive"}
    gross = long_v + short_v
    net = long_v - short_v
    return {
        "ok": True,
        "capital": round(cap, 2),
        "long": round(long_v, 2),
        "short": round(short_v, 2),
        "gross_exposure": round(gross, 2),
        "net_exposure": round(net, 2),
        "gross_pct": round((gross / cap) * 100.0, 1),
        "net_pct": round((net / cap) * 100.0, 1),
        "long_pct": round((long_v / cap) * 100.0, 1),
        "short_pct": round((short_v / cap) * 100.0, 1),
        "cash_pct": round(((cap - long_v) / cap) * 100.0, 1),
        "leverage": round(gross / cap, 2),
        "market_neutral": abs(net / cap) < 0.05,
    }


# ---------------------------------------------------------------------------
# Position and portfolio P&L
# ---------------------------------------------------------------------------
def position_pnl(
    *,
    side: str,
    entry: Any,
    exit_price: Any,
    position_size: Any,
    financing_cost_pct: Any = 0.0,
) -> dict[str, Any]:
    """P&L on one leg. A short gains when the price falls."""
    e, x, size = _num(entry), _num(exit_price), _num(position_size)
    if e <= 0 or size <= 0:
        return {"ok": False, "error": "entry_and_size_required"}
    direction = -1.0 if str(side or "long").lower().startswith("s") else 1.0
    move_pct = ((x - e) / e) * 100.0 * direction
    gross = size * (move_pct / 100.0)
    financing = size * (_num(financing_cost_pct) / 100.0)
    return {
        "ok": True,
        "side": "short" if direction < 0 else "long",
        "entry": round(e, 2),
        "exit": round(x, 2),
        "position_size": round(size, 2),
        "move_pct": round(move_pct, 2),
        "gross_pnl": round(gross, 2),
        "financing_cost": round(financing, 2),
        "net_pnl": round(gross - financing, 2),
    }


def portfolio_pnl(legs: list[dict[str, Any]], capital: Any = None) -> dict[str, Any]:
    """Aggregate P&L across legs."""
    results = []
    for leg in legs or []:
        results.append(
            position_pnl(
                side=leg.get("side", "long"),
                entry=leg.get("entry"),
                exit_price=leg.get("exit"),
                position_size=leg.get("size"),
                financing_cost_pct=leg.get("financing_cost_pct", 0.0),
            )
        )
    valid = [r for r in results if r.get("ok")]
    total = sum(r["net_pnl"] for r in valid)
    long_pnl = sum(r["net_pnl"] for r in valid if r["side"] == "long")
    short_pnl = sum(r["net_pnl"] for r in valid if r["side"] == "short")
    cap = _num(capital)
    return {
        "ok": True,
        "legs": results,
        "long_pnl": round(long_pnl, 2),
        "short_pnl": round(short_pnl, 2),
        "total_pnl": round(total, 2),
        "return_on_capital_pct": round((total / cap) * 100.0, 2) if cap > 0 else None,
    }


# ---------------------------------------------------------------------------
# Pair trade / statistical arbitrage
# ---------------------------------------------------------------------------
def pair_signal(
    spread_now: Any,
    spread_mean: Any,
    spread_std: Any,
    *,
    entry_z: Any = 2.0,
    exit_z: Any = 0.5,
) -> dict[str, Any]:
    """Z-score and the trade it implies."""
    now, mean, std = _num(spread_now), _num(spread_mean), _num(spread_std)
    if std <= 0:
        return {"ok": False, "error": "std_must_be_positive"}
    z = (now - mean) / std
    entry, exit_threshold = _num(entry_z, 2.0), _num(exit_z, 0.5)
    if z >= entry:
        signal, action = "short_spread", "Spread is stretched wide: short the outperformer, long the laggard"
    elif z <= -entry:
        signal, action = "long_spread", "Spread is compressed: long the laggard, short the outperformer"
    elif abs(z) <= exit_threshold:
        signal, action = "exit", "Spread has reverted to its mean — close the position"
    else:
        signal, action = "hold", "Inside the band — no trade"
    return {
        "ok": True,
        "z_score": round(z, 2),
        "spread": round(now, 4),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "deviation": round(now - mean, 4),
        "entry_threshold": entry,
        "exit_threshold": exit_threshold,
        "signal": signal,
        "action": action,
    }


def pair_diagnostics(
    long_prices: list[Any],
    short_prices: list[Any],
    *,
    entry_z: Any = 2.0,
    exit_z: Any = 0.5,
    max_half_life_sessions: Any = 60,
) -> dict[str, Any]:
    """Pre-trade pair diagnostics using aligned price histories.

    This is deliberately stricter than a valuation-gap screen.  It estimates a
    hedge ratio, residual z-score and mean-reversion half-life, then reports a
    candidate only when the relationship passes all coverage checks.  It does
    not claim a p-value without a statistical package and therefore never
    mislabels correlation as cointegration.
    """
    x = [_num(v, float("nan")) for v in long_prices or []]
    y = [_num(v, float("nan")) for v in short_prices or []]
    pairs = [(a, b) for a, b in zip(x, y) if a > 0 and b > 0 and math.isfinite(a) and math.isfinite(b)]
    if len(pairs) < 120:
        return {"ok": False, "error": "insufficient_aligned_history", "required_sessions": 120,
                "available_sessions": len(pairs), "research_status": "not_tradeable"}
    lx, ly = [math.log(a) for a, _ in pairs], [math.log(b) for _, b in pairs]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    var_y = sum((item - my) ** 2 for item in ly)
    if var_y <= 1e-12:
        return {"ok": False, "error": "constant_leg", "research_status": "not_tradeable"}
    hedge_ratio = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / var_y
    intercept = mx - hedge_ratio * my
    residuals = [a - (intercept + hedge_ratio * b) for a, b in zip(lx, ly)]
    mean = sum(residuals) / len(residuals)
    variance = sum((item - mean) ** 2 for item in residuals) / (len(residuals) - 1)
    std = math.sqrt(variance)
    if std <= 1e-12:
        return {"ok": False, "error": "constant_spread", "research_status": "not_tradeable"}
    # AR(1) residual fit: delta(s) = alpha + beta * s(t-1).  beta < 0 implies reversion.
    lag, delta = residuals[:-1], [residuals[i] - residuals[i - 1] for i in range(1, len(residuals))]
    lag_mean, delta_mean = sum(lag) / len(lag), sum(delta) / len(delta)
    denom = sum((item - lag_mean) ** 2 for item in lag)
    beta = sum((a - lag_mean) * (b - delta_mean) for a, b in zip(lag, delta)) / denom if denom else 0.0
    half_life = math.log(2) / -beta if beta < 0 else None
    correlation = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / math.sqrt(
        sum((a - mx) ** 2 for a in lx) * sum((b - my) ** 2 for b in ly)
    )
    signal = pair_signal(residuals[-1], mean, std, entry_z=entry_z, exit_z=exit_z)
    max_half_life = _num(max_half_life_sessions, 60.0)
    eligible = bool(abs(correlation) >= 0.6 and half_life is not None and 1 <= half_life <= max_half_life)
    return {
        "ok": True,
        "research_status": "pair_candidate" if eligible else "not_tradeable",
        "eligible_for_research_queue": eligible,
        "observations": len(pairs),
        "hedge_ratio": round(hedge_ratio, 5),
        "intercept": round(intercept, 5),
        "log_price_correlation": round(correlation, 4),
        "residual_z_score": signal.get("z_score"),
        "signal": signal.get("signal"),
        "estimated_half_life_sessions": round(half_life, 2) if half_life is not None else None,
        "adf_status": "not_estimated_without_statistical_test_dependency",
        "limitations": [
            "A valuation gap and correlation do not establish cointegration.",
            "Borrow availability, financing, corporate actions and execution costs must pass before any trade simulation.",
        ],
    }


# ---------------------------------------------------------------------------
# Strategy expectancy
# ---------------------------------------------------------------------------
def strategy_expectancy(
    *,
    hit_rate_pct: Any,
    avg_win_pct: Any,
    avg_loss_pct: Any,
    trades_per_year: Any,
    leverage: Any = 1.0,
    cost_per_trade_pct: Any = 0.0,
    volatility_pct: Any = None,
) -> dict[str, Any]:
    """Expectancy, Sharpe, Kelly and a drawdown estimate from trade statistics."""
    p = max(0.0, min(1.0, _num(hit_rate_pct) / 100.0))
    win = _num(avg_win_pct) / 100.0
    loss = abs(_num(avg_loss_pct)) / 100.0
    n = max(0.0, _num(trades_per_year))
    lev = max(0.0, _num(leverage, 1.0))
    cost = _num(cost_per_trade_pct) / 100.0

    if win <= 0 or loss <= 0 or n <= 0:
        return {"ok": False, "error": "win_loss_and_trades_required"}

    edge_per_trade = (p * win) - ((1 - p) * loss) - cost
    annual_return = edge_per_trade * n * lev

    # Trade-level dispersion → annualised volatility.
    variance = (p * (win - edge_per_trade) ** 2) + ((1 - p) * (-loss - edge_per_trade) ** 2)
    trade_vol = math.sqrt(max(0.0, variance))
    annual_vol = trade_vol * math.sqrt(n) * lev
    if volatility_pct is not None:
        annual_vol = _num(volatility_pct) / 100.0

    sharpe = (annual_return / annual_vol) if annual_vol > 0 else None

    # Kelly fraction on a win/loss payoff.
    payoff = win / loss
    kelly = ((p * (payoff + 1)) - 1) / payoff if payoff > 0 else 0.0

    # Rough drawdown expectation: Sharpe-scaled, floored so it is never flattering.
    if sharpe and sharpe > 0:
        est_dd = annual_vol / max(0.5, sharpe)
    else:
        est_dd = annual_vol * 2.0

    return {
        "ok": True,
        "edge_per_trade_pct": round(edge_per_trade * 100.0, 3),
        "expected_annual_return_pct": round(annual_return * 100.0, 2),
        "expected_volatility_pct": round(annual_vol * 100.0, 2),
        "sharpe": round(sharpe, 2) if sharpe is not None else None,
        "kelly_fraction": round(max(0.0, min(1.0, kelly)), 3),
        "half_kelly": round(max(0.0, min(1.0, kelly)) / 2.0, 3),
        "estimated_max_drawdown_pct": round(est_dd * 100.0, 2),
        "profit_factor": round((p * win) / ((1 - p) * loss), 2) if (1 - p) * loss > 0 else None,
        "breakeven_hit_rate_pct": round((loss / (win + loss)) * 100.0, 1),
        "inputs": {
            "hit_rate_pct": round(p * 100.0, 1),
            "avg_win_pct": round(win * 100.0, 2),
            "avg_loss_pct": round(loss * 100.0, 2),
            "trades_per_year": n,
            "leverage": lev,
            "cost_per_trade_pct": round(cost * 100.0, 3),
        },
        "note": (
            "Expectancy from trade statistics, not a backtest. Kelly is shown because "
            "professionals size below it, not at it."
        ),
        "realism_warning": (
            "This assumes every trade risks the full book and that edge repeats "
            f"{int(n)} times a year independently. Real capacity, slippage and "
            "correlated losses compress this materially — treat it as an upper bound."
            if annual_return > 0.60
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Attribution and risk
# ---------------------------------------------------------------------------
def attribution(components: dict[str, Any]) -> dict[str, Any]:
    """Waterfall from return components to the total."""
    steps = []
    running = 0.0
    for label, value in (components or {}).items():
        v = _num(value)
        running += v
        steps.append({"label": label.replace("_", " ").title(), "value": round(v, 2), "cumulative": round(running, 2)})
    return {"ok": True, "steps": steps, "total": round(running, 2)}


def risk_metrics(
    *,
    annual_return_pct: Any,
    annual_vol_pct: Any,
    beta: Any = 0.0,
    leverage: Any = 1.0,
    confidence: Any = 95,
) -> dict[str, Any]:
    """VaR, expected shortfall and the standard risk gauges."""
    ret = _num(annual_return_pct) / 100.0
    vol = _num(annual_vol_pct) / 100.0
    if vol <= 0:
        return {"ok": False, "error": "volatility_required"}

    conf = _num(confidence, 95)
    z = {90: 1.2816, 95: 1.6449, 99: 2.3263}.get(int(conf), 1.6449)
    daily_vol = vol / math.sqrt(252)
    var = z * daily_vol
    # Expected shortfall for a normal tail.
    es = daily_vol * (math.exp(-(z**2) / 2) / (math.sqrt(2 * math.pi) * (1 - conf / 100.0)))

    sharpe = ret / vol
    return {
        "ok": True,
        "daily_var_pct": round(var * 100.0, 2),
        "expected_shortfall_pct": round(es * 100.0, 2),
        "confidence": int(conf),
        "annual_volatility_pct": round(vol * 100.0, 2),
        "sharpe": round(sharpe, 2),
        "beta": round(_num(beta), 2),
        "leverage": round(_num(leverage, 1.0), 2),
        "estimated_max_drawdown_pct": round((vol / max(0.5, sharpe)) * 100.0, 2),
    }


def volatility_scenarios(
    base_vol_pct: Any, annual_return_pct: Any, scenarios: Optional[list[Any]] = None
) -> dict[str, Any]:
    """How the risk profile changes as volatility rises."""
    base = _num(base_vol_pct)
    ret = _num(annual_return_pct)
    levels = scenarios or [base, base * 1.667, base * 2.667]
    out = []
    for level in levels:
        pack = risk_metrics(annual_return_pct=ret, annual_vol_pct=level)
        if pack.get("ok"):
            out.append(
                {
                    "volatility_pct": round(_num(level), 1),
                    "sharpe": pack["sharpe"],
                    "daily_var_pct": pack["daily_var_pct"],
                    "estimated_max_drawdown_pct": pack["estimated_max_drawdown_pct"],
                }
            )
    return {"ok": True, "base_return_pct": round(ret, 2), "scenarios": out}
