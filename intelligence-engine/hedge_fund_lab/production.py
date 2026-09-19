"""Hedge Fund Strategy Lab — production API."""

from __future__ import annotations

from typing import Any

from hedge_fund_lab import calculators
from hedge_fund_lab.strategies import STRATEGIES, comparison, get_strategy, list_strategies


def health() -> dict[str, Any]:
    from .scanner import universe_meta

    meta = universe_meta()
    # Touch the universe once so meta reflects live warehouse coverage.
    if not meta.get("count"):
        try:
            from .scanner import _universe

            _universe()
            meta = universe_meta()
        except Exception:
            pass
    status = "ok" if meta.get("count") else "empty"
    return {
        "ok": True,
        "engine": "hedge_fund_lab",
        "status": status,
        "strategies": len(STRATEGIES),
        "families": sorted({s["family"] for s in STRATEGIES}),
        "page": "Hedge Fund Strategy Lab",
        "universe": meta,
        "live_feed": meta.get("source") == "warehouse+market_intelligence",
    }


def library() -> dict[str, Any]:
    return {"ok": True, "strategies": list_strategies(), "count": len(STRATEGIES)}


def strategy(strategy_id: str) -> dict[str, Any]:
    pack = get_strategy(strategy_id)
    if not pack:
        return {"ok": False, "error": "unknown_strategy", "strategy_id": strategy_id}

    if pack["id"] in {"long_short_equity", "equity_market_neutral"}:
        institutional_use = (
            f"{pack['name']} seeks to reduce dependence on market direction through "
            f"offsetting long and short exposures, but returns remain sensitive to net beta, "
            f"factor exposures and short squeezes. Its stated alpha source is {pack['alpha_source'].lower()}."
        )
    else:
        institutional_use = (
            f"{pack['name']} seeks {pack['alpha_source'].lower()} across its stated "
            f"{pack['holding_period'].lower()} holding period. Returns remain exposed to the "
            "strategy-specific risks and regimes shown below."
        )

    # AGI Intelligence panel — the interpretation layer over the profile.
    intelligence = {
        "why_institutions_use_it": institutional_use,
        "when_it_performs": pack["works_when"],
        "when_it_struggles": pack["fails_when"],
        "favourable_regimes": pack["regimes"],
        "risk_factors": pack["risk_factors"],
        "monitored_kpis": pack["kpis"],
        "common_mistakes": pack["mistakes"],
        "critical_data": pack["key_data"],
        "bottom_line": (
            f"The edge is {pack['alpha_source'].lower()}, held for "
            f"{pack['holding_period']}. It pays when {pack['works_when'][0].lower()}, "
            f"and it breaks when {pack['fails_when'][0].lower()}."
        ),
    }
    out = {"ok": True, **pack, "agi_intelligence": intelligence}
    if pack["id"] == "long_short_equity":
        from .long_short_equity import readiness

        out["institutional_platform"] = readiness()
    return out


def compare() -> dict[str, Any]:
    return {"ok": True, "rows": comparison()}


def calculate(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the calculator the UI asked for."""
    body = payload or {}
    name = str(kind or "").strip().lower()

    if name == "exposure":
        return calculators.exposure(body.get("capital"), body.get("long"), body.get("short"))
    if name == "position_pnl":
        return calculators.position_pnl(
            side=body.get("side", "long"),
            entry=body.get("entry"),
            exit_price=body.get("exit"),
            position_size=body.get("size"),
            financing_cost_pct=body.get("financing_cost_pct", 0.0),
        )
    if name == "portfolio_pnl":
        return calculators.portfolio_pnl(body.get("legs") or [], body.get("capital"))
    if name == "pair_signal":
        return calculators.pair_signal(
            body.get("spread"),
            body.get("mean"),
            body.get("std"),
            entry_z=body.get("entry_z", 2.0),
            exit_z=body.get("exit_z", 0.5),
        )
    if name == "pair_diagnostics":
        return calculators.pair_diagnostics(
            body.get("long_prices") or [], body.get("short_prices") or [],
            entry_z=body.get("entry_z", 2.0), exit_z=body.get("exit_z", 0.5),
            max_half_life_sessions=body.get("max_half_life_sessions", 60),
        )
    if name == "expectancy":
        return calculators.strategy_expectancy(
            hit_rate_pct=body.get("hit_rate_pct"),
            avg_win_pct=body.get("avg_win_pct"),
            avg_loss_pct=body.get("avg_loss_pct"),
            trades_per_year=body.get("trades_per_year"),
            leverage=body.get("leverage", 1.0),
            cost_per_trade_pct=body.get("cost_per_trade_pct", 0.0),
            volatility_pct=body.get("volatility_pct"),
        )
    if name == "attribution":
        return calculators.attribution(body.get("components") or {})
    if name == "risk":
        return calculators.risk_metrics(
            annual_return_pct=body.get("annual_return_pct"),
            annual_vol_pct=body.get("annual_vol_pct"),
            beta=body.get("beta", 0.0),
            leverage=body.get("leverage", 1.0),
            confidence=body.get("confidence", 95),
        )
    if name == "volatility_scenarios":
        return calculators.volatility_scenarios(
            body.get("base_vol_pct"),
            body.get("annual_return_pct"),
            body.get("scenarios"),
        )
    return {"ok": False, "error": "unknown_calculator", "kind": name}


def backtest(strategy_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from .backtests import run_from_warehouse

    return run_from_warehouse(strategy_id, payload or {})


def terminal(limit: int = 12) -> dict[str, Any]:
    """The full hedge fund terminal surface in one call."""
    from .terminal import overview

    return overview(limit=limit)


def terminal_scan(strategy: str, limit: int = 20, sector: str | None = None) -> dict[str, Any]:
    from .terminal import scan

    return scan(strategy, limit=limit, sector=sector)


def terminal_opportunity(ticker: str) -> dict[str, Any]:
    from .terminal import opportunity

    return opportunity(ticker)
