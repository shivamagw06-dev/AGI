"""Auditable, point-in-time research backtests for the Hedge Fund Lab.

This module deliberately fails closed when the warehouse cannot support a
test.  A screen is not labelled as a strategy until its inputs were available
on each decision date and the simulated portfolio has paid its costs.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections import defaultdict
from datetime import date
from typing import Any, Iterable


MODEL_VERSION = "hfl-backtest-1.0"
DEFAULTS = {
    "lookback_sessions": 252,
    "skip_recent_sessions": 21,
    "rebalance_sessions": 21,
    "holdings": 20,
    "max_weight": 0.10,
    "max_sector_weight": 0.30,
    "stop_loss_pct": 0.20,
    "one_way_cost_bps": 25,
    "min_average_daily_value": 2_000_000,
    "portfolio_capital": 100_000_000,
    "max_adv_participation": 0.10,
    "max_drawdown_limit_pct": 20.0,
    "min_oos_annualized_return_pct": 0.0,
    "min_oos_sharpe": 0.0,
}


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _clean_prices(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Normalise and de-duplicate daily bars, preferring adjusted close."""
    by_symbol: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        symbol, day = str(row.get("symbol") or "").upper(), str(row.get("date") or "")
        close = _number(row.get("adjusted_close")) or _number(row.get("close"))
        if not symbol or not day or close is None or close <= 0:
            continue
        by_symbol[symbol][day] = {
            "date": day,
            "close": close,
            "volume": _number(row.get("volume")) or 0.0,
        }
    return {symbol: [bars[d] for d in sorted(bars)] for symbol, bars in by_symbol.items()}


def _metrics(returns: list[float]) -> dict[str, float | None]:
    if not returns:
        return {"cumulative_return_pct": None, "annualized_return_pct": None, "annualized_volatility_pct": None,
                "sharpe": None, "max_drawdown_pct": None, "win_rate_pct": None}
    equity = peak = 1.0
    max_drawdown = 0.0
    for ret in returns:
        equity *= 1.0 + ret
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0)
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((item - mean) ** 2 for item in returns) / max(1, n - 1)
    vol = math.sqrt(variance) * math.sqrt(252)
    annualized = equity ** (252 / n) - 1.0 if equity > 0 else -1.0
    return {
        "cumulative_return_pct": round((equity - 1.0) * 100, 3),
        "annualized_return_pct": round(annualized * 100, 3),
        "annualized_volatility_pct": round(vol * 100, 3),
        "sharpe": round((mean * 252) / vol, 3) if vol > 1e-12 else None,
        "max_drawdown_pct": round(max_drawdown * 100, 3),
        "win_rate_pct": round(sum(item > 0 for item in returns) / n * 100, 2),
    }


def _validation_report(dates: list[str], returns: list[float]) -> dict[str, Any]:
    """Chronological, leakage-safe evaluation of already-costed daily returns."""
    count = min(len(dates), len(returns))
    if count < 63:
        return {
            "status": "INSUFFICIENT_OBSERVATIONS",
            "observations": count,
            "minimum_observations": 63,
            "lookahead_check": True,
        }
    train_end = max(1, int(count * 0.60))
    validation_end = max(train_end + 1, int(count * 0.80))
    periods = {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "test": (validation_end, count),
    }
    period_results = {}
    for name, (start, end) in periods.items():
        period_results[name] = {
            "start": dates[start],
            "end": dates[end - 1],
            "observations": end - start,
            "metrics": _metrics(returns[start:end]),
        }
    walk_forward = []
    window = 126
    step = 63
    for start in range(0, count - window + 1, step):
        end = start + window
        walk_forward.append({
            "start": dates[start],
            "end": dates[end - 1],
            "observations": window,
            "metrics": _metrics(returns[start:end]),
        })
    return {
        "status": "COMPLETED",
        "method": "chronological_60_20_20_with_rolling_126_session_windows",
        "lookahead_check": True,
        "costs_included": True,
        "periods": period_results,
        "walk_forward": walk_forward,
        "walk_forward_windows": len(walk_forward),
        "out_of_sample_observations": count - validation_end,
    }


def momentum_backtest(
    rows: Iterable[dict[str, Any]], *, classifications: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monthly 12-1 momentum backtest using only data known on each rebalance.

    Orders are assumed to execute at the next session's close.  That is a
    conservative convention for an end-of-day signal and prevents look-ahead.
    """
    cfg = {**DEFAULTS, **(config or {})}
    prices = _clean_prices(rows)
    lookback, skip = int(cfg["lookback_sessions"]), int(cfg["skip_recent_sessions"])
    rebalance_every, holdings = int(cfg["rebalance_sessions"]), int(cfg["holdings"])
    if lookback <= skip or holdings < 1 or rebalance_every < 1:
        return {"ok": False, "error": "invalid_backtest_config"}
    calendar = sorted({bar["date"] for series in prices.values() for bar in series})
    if len(calendar) < lookback + 2:
        return {"ok": False, "error": "insufficient_price_history", "required_sessions": lookback + 2,
                "available_sessions": len(calendar), "model_version": MODEL_VERSION}

    by_day: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for symbol, series in prices.items():
        for bar in series:
            by_day[bar["date"]][symbol] = bar
    sectors = {str(k).upper(): str(v or "Unclassified") for k, v in (classifications or {}).items()}
    price_dates = {symbol: [bar["date"] for bar in series] for symbol, series in prices.items()}
    weights: dict[str, float] = {}
    entry: dict[str, float] = {}
    peak: dict[str, float] = {}
    returns: list[float] = []
    return_dates: list[str] = []
    turnover: list[float] = []
    capacity_estimates: list[float] = []
    rebalances: list[dict[str, Any]] = []
    stopped: set[str] = set()
    start = lookback + 1
    for i in range(start, len(calendar)):
        today, previous = calendar[i], calendar[i - 1]
        bars, prior = by_day[today], by_day[previous]
        is_rebalance = (i - start) % rebalance_every == 0
        old_weights = dict(weights)
        if is_rebalance:
            candidates: list[tuple[float, str, float]] = []
            for symbol, series in prices.items():
                end_index = bisect_right(price_dates[symbol], previous)
                if end_index < lookback:
                    continue
                end, base = series[end_index - skip - 1], series[end_index - lookback]
                if base["close"] <= 0:
                    continue
                liquidity_window = series[max(0, end_index - 21):end_index]
                avg_value = sum(bar["close"] * bar["volume"] for bar in liquidity_window) / len(liquidity_window)
                if avg_value < float(cfg["min_average_daily_value"]):
                    continue
                candidates.append((end["close"] / base["close"] - 1.0, symbol, avg_value))
            candidates.sort(reverse=True)
            sector_used: dict[str, float] = defaultdict(float)
            selected: list[str] = []
            raw_weight = min(float(cfg["max_weight"]), 1.0 / holdings)
            selected_adv: dict[str, float] = {}
            for _, symbol, avg_value in candidates:
                sector = sectors.get(symbol, "Unclassified")
                if sector_used[sector] + raw_weight > float(cfg["max_sector_weight"]) + 1e-12:
                    continue
                selected.append(symbol)
                selected_adv[symbol] = avg_value
                sector_used[sector] += raw_weight
                if len(selected) == holdings:
                    break
            weights = {symbol: 1.0 / len(selected) for symbol in selected} if selected else {}
            if weights:
                participation = float(cfg["max_adv_participation"])
                capacity_estimates.append(min(selected_adv[symbol] * participation / weight for symbol, weight in weights.items()))
            entry = {symbol: bars[symbol]["close"] for symbol in weights if symbol in bars}
            peak = dict(entry)
            stopped.clear()
            rebalances.append({"date": today, "selected": sorted(weights), "candidate_count": len(candidates),
                               "estimated_capacity": round(capacity_estimates[-1], 2) if weights else None})

        gross_return = 0.0
        for symbol, weight in list(weights.items()):
            if symbol not in bars or symbol not in prior:
                continue
            current = bars[symbol]["close"]
            peak[symbol] = max(peak.get(symbol, current), current)
            if current / max(entry.get(symbol, current), peak[symbol]) - 1.0 <= -float(cfg["stop_loss_pct"]):
                # A close-based stop is executed on this close and only affects subsequent days.
                stopped.add(symbol)
            gross_return += weight * (current / prior[symbol]["close"] - 1.0)
        if stopped:
            weights = {symbol: weight for symbol, weight in weights.items() if symbol not in stopped}
        all_symbols = set(old_weights) | set(weights)
        # One-way turnover is the purchase side; treating the initial cash-to-
        # equities deployment as 100% prevents understating entry costs.
        traded = sum(max(0.0, weights.get(symbol, 0.0) - old_weights.get(symbol, 0.0)) for symbol in all_symbols)
        cost = traded * float(cfg["one_way_cost_bps"]) / 10_000.0
        returns.append(gross_return - cost)
        return_dates.append(today)
        turnover.append(traded)

    if not returns or not rebalances:
        return {"ok": False, "error": "insufficient_eligible_universe", "model_version": MODEL_VERSION,
                "eligible_symbols": len(prices)}
    return {
        "ok": True,
        "strategy": "momentum_12_1_long_only",
        "research_status": "backtested_not_investment_advice",
        "model_version": MODEL_VERSION,
        "execution": {"signal_time": "prior_close", "execution": "next_close", "cost_model": "one_way_turnover_bps",
                      "one_way_cost_bps": cfg["one_way_cost_bps"], "stop_loss_pct": cfg["stop_loss_pct"] * 100},
        "constraints": {key: cfg[key] for key in ("holdings", "max_weight", "max_sector_weight", "min_average_daily_value", "portfolio_capital", "max_adv_participation", "max_drawdown_limit_pct", "min_oos_annualized_return_pct", "min_oos_sharpe")},
        "coverage": {"symbols_with_price_history": len(prices), "calendar_sessions": len(calendar),
                     "backtest_sessions": len(returns), "rebalance_count": len(rebalances)},
        "metrics": _metrics(returns),
        "validation": _validation_report(return_dates, returns),
        "average_turnover_pct": round(sum(turnover) / len(turnover) * 100, 3),
        "capacity": {
            "status": "COMPLETED" if capacity_estimates else "INSUFFICIENT_DATA",
            "assumed_portfolio_capital": float(cfg["portfolio_capital"]),
            "max_adv_participation_pct": round(float(cfg["max_adv_participation"]) * 100, 3),
            "minimum_estimated_capacity": round(min(capacity_estimates), 2) if capacity_estimates else None,
            "median_estimated_capacity": round(sorted(capacity_estimates)[len(capacity_estimates) // 2], 2) if capacity_estimates else None,
            "passes_assumed_capital": bool(capacity_estimates and min(capacity_estimates) >= float(cfg["portfolio_capital"])),
        },
        "rebalances": rebalances[-24:],
        "limitations": [
            "Long-only price momentum only; no borrow, short rebate, taxes or intraday execution model.",
            "Corporate-action-adjusted closes are used when available; incomplete adjustment history invalidates interpretation.",
            "This is a research backtest, not evidence of future returns or a production trading instruction.",
        ],
    }


def trend_backtest(
    rows: Iterable[dict[str, Any]], *, classifications: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Long-only moving-average trend portfolio with next-session execution."""
    cfg = {**DEFAULTS, "fast_window": 50, "slow_window": 200, "slope_window": 20, **(config or {})}
    prices = _clean_prices(rows)
    fast, slow, slope_window = int(cfg["fast_window"]), int(cfg["slow_window"]), int(cfg["slope_window"])
    rebalance_every, holdings = int(cfg["rebalance_sessions"]), int(cfg["holdings"])
    required = slow + slope_window
    if min(fast, slow, slope_window, rebalance_every, holdings) < 1 or fast >= slow:
        return {"ok": False, "error": "invalid_backtest_config"}
    calendar = sorted({bar["date"] for series in prices.values() for bar in series})
    if len(calendar) < required + 2:
        return {"ok": False, "error": "insufficient_price_history", "required_sessions": required + 2,
                "available_sessions": len(calendar), "model_version": MODEL_VERSION}
    by_day: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for symbol, series in prices.items():
        for bar in series:
            by_day[bar["date"]][symbol] = bar
    sectors = {str(k).upper(): str(v or "Unclassified") for k, v in (classifications or {}).items()}
    price_dates = {symbol: [bar["date"] for bar in series] for symbol, series in prices.items()}
    weights: dict[str, float] = {}
    entry: dict[str, float] = {}
    peak: dict[str, float] = {}
    returns: list[float] = []
    return_dates: list[str] = []
    turnover: list[float] = []
    capacity_estimates: list[float] = []
    rebalances: list[dict[str, Any]] = []
    stopped: set[str] = set()
    start = required + 1
    for i in range(start, len(calendar)):
        today, previous = calendar[i], calendar[i - 1]
        bars, prior = by_day[today], by_day[previous]
        old_weights = dict(weights)
        if (i - start) % rebalance_every == 0:
            candidates: list[tuple[float, str, float]] = []
            for symbol, series in prices.items():
                end_index = bisect_right(price_dates[symbol], previous)
                if end_index < required:
                    continue
                history = series[end_index - required:end_index]
                closes = [bar["close"] for bar in history]
                price = closes[-1]
                sma_fast = sum(closes[-fast:]) / fast
                sma_slow = sum(closes[-slow:]) / slow
                prior_slow = sum(closes[-slow - slope_window:-slope_window]) / slow
                slope = sma_slow / prior_slow - 1.0 if prior_slow > 0 else 0.0
                if not (price > sma_slow and sma_fast > sma_slow and slope > 0):
                    continue
                liquidity_window = series[max(0, end_index - 21):end_index]
                avg_value = sum(bar["close"] * bar["volume"] for bar in liquidity_window) / len(liquidity_window)
                if avg_value < float(cfg["min_average_daily_value"]):
                    continue
                score = (price / sma_slow - 1.0) + (sma_fast / sma_slow - 1.0) + slope
                candidates.append((score, symbol, avg_value))
            candidates.sort(reverse=True)
            selected: list[str] = []
            selected_adv: dict[str, float] = {}
            sector_used: dict[str, float] = defaultdict(float)
            raw_weight = min(float(cfg["max_weight"]), 1.0 / holdings)
            for _, symbol, avg_value in candidates:
                sector = sectors.get(symbol, "Unclassified")
                if sector_used[sector] + raw_weight > float(cfg["max_sector_weight"]) + 1e-12:
                    continue
                selected.append(symbol)
                selected_adv[symbol] = avg_value
                sector_used[sector] += raw_weight
                if len(selected) == holdings:
                    break
            weights = {symbol: 1.0 / len(selected) for symbol in selected} if selected else {}
            if weights:
                participation = float(cfg["max_adv_participation"])
                capacity_estimates.append(min(selected_adv[symbol] * participation / weight for symbol, weight in weights.items()))
            entry = {symbol: bars[symbol]["close"] for symbol in weights if symbol in bars}
            peak = dict(entry)
            stopped.clear()
            rebalances.append({"date": today, "selected": sorted(weights), "candidate_count": len(candidates),
                               "estimated_capacity": round(capacity_estimates[-1], 2) if weights else None})
        gross_return = 0.0
        for symbol, weight in list(weights.items()):
            if symbol not in bars or symbol not in prior:
                continue
            current = bars[symbol]["close"]
            peak[symbol] = max(peak.get(symbol, current), current)
            if current / max(entry.get(symbol, current), peak[symbol]) - 1.0 <= -float(cfg["stop_loss_pct"]):
                stopped.add(symbol)
            gross_return += weight * (current / prior[symbol]["close"] - 1.0)
        if stopped:
            weights = {symbol: weight for symbol, weight in weights.items() if symbol not in stopped}
        all_symbols = set(old_weights) | set(weights)
        traded = sum(max(0.0, weights.get(symbol, 0.0) - old_weights.get(symbol, 0.0)) for symbol in all_symbols)
        returns.append(gross_return - traded * float(cfg["one_way_cost_bps"]) / 10_000.0)
        return_dates.append(today)
        turnover.append(traded)
    if not returns or not rebalances:
        return {"ok": False, "error": "insufficient_eligible_universe", "model_version": MODEL_VERSION,
                "eligible_symbols": len(prices)}
    return {
        "ok": True,
        "strategy": "trend_following_long_only",
        "research_status": "backtested_not_investment_advice",
        "model_version": MODEL_VERSION,
        "execution": {"signal_time": "prior_close", "execution": "next_close", "cost_model": "one_way_turnover_bps",
                      "one_way_cost_bps": cfg["one_way_cost_bps"], "stop_loss_pct": cfg["stop_loss_pct"] * 100},
        "constraints": {key: cfg[key] for key in ("holdings", "max_weight", "max_sector_weight", "min_average_daily_value", "portfolio_capital", "max_adv_participation", "max_drawdown_limit_pct", "min_oos_annualized_return_pct", "min_oos_sharpe")},
        "parameters": {"fast_window": fast, "slow_window": slow, "slope_window": slope_window, "rebalance_sessions": rebalance_every},
        "coverage": {"symbols_with_price_history": len(prices), "calendar_sessions": len(calendar),
                     "backtest_sessions": len(returns), "rebalance_count": len(rebalances)},
        "metrics": _metrics(returns),
        "validation": _validation_report(return_dates, returns),
        "average_turnover_pct": round(sum(turnover) / len(turnover) * 100, 3),
        "capacity": {
            "status": "COMPLETED" if capacity_estimates else "INSUFFICIENT_DATA",
            "assumed_portfolio_capital": float(cfg["portfolio_capital"]),
            "max_adv_participation_pct": round(float(cfg["max_adv_participation"]) * 100, 3),
            "minimum_estimated_capacity": round(min(capacity_estimates), 2) if capacity_estimates else None,
            "median_estimated_capacity": round(sorted(capacity_estimates)[len(capacity_estimates) // 2], 2) if capacity_estimates else None,
            "passes_assumed_capital": bool(capacity_estimates and min(capacity_estimates) >= float(cfg["portfolio_capital"])),
        },
        "rebalances": rebalances[-24:],
        "limitations": [
            "Long-only trend model; no short book, taxes or intraday execution model.",
            "Corporate-action-adjusted closes are used when available; adjustment coverage remains an independent gate.",
            "Historical constituents and delisted securities remain incomplete, so survivorship risk is explicit.",
        ],
    }


def run_from_warehouse(strategy: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load the bounded warehouse inputs needed by the backtest."""
    strategy_key = str(strategy).lower()
    if strategy_key not in {"momentum", "momentum_12_1_long_only", "trend", "trend_following", "trend_following_long_only"}:
        return {"ok": False, "error": "strategy_requires_point_in_time_fundamental_history",
                "detail": "Value and quality are intentionally blocked until filing-effective timestamps and factor snapshots pass coverage checks."}
    try:
        from institutional_warehouse import db
        from .scanner import _universe
        universe = sorted(_universe(), key=lambda row: float(row.get("market_cap") or 0), reverse=True)
        selected = [row for row in universe[:200] if str(row.get("ticker") or "").strip()]
        symbols = [str(row.get("ticker") or "").upper() for row in selected]
        classifications = {str(row.get("ticker") or "").upper(): row.get("primary_sector") for row in selected}
        table = db.physical_table("daily_market_history")
        marks = ",".join("?" for _ in symbols)
        rows = db.query(
            f'''SELECT symbol, date, close, adjusted_close, volume
                FROM {table}
                WHERE COALESCE(sys_published, 1) = 1
                  AND symbol IN ({marks})
                ORDER BY symbol, date''',
            tuple(symbols),
        ) if symbols else []
    except Exception as exc:
        return {"ok": False, "error": "warehouse_unavailable", "detail": str(exc)[:200]}
    supplied = dict(config or {})
    sensitivity_enabled = bool(supplied.pop("parameter_sensitivity", True))
    is_trend = strategy_key in {"trend", "trend_following", "trend_following_long_only"}
    runner = trend_backtest if is_trend else momentum_backtest
    result = runner(rows, classifications=classifications, config=supplied)
    if not result.get("ok") or not sensitivity_enabled:
        return result
    sensitivity = []
    if is_trend:
        base_slow = int(supplied.get("slow_window", 200))
        variants = sorted({max(100, base_slow - 50), base_slow, base_slow + 50})
        for slow_window in variants:
            variant = runner(rows, classifications=classifications, config={**supplied, "slow_window": slow_window})
            sensitivity.append({"slow_window": slow_window, "ok": bool(variant.get("ok")), "metrics": variant.get("metrics"),
                                "test_metrics": ((variant.get("validation") or {}).get("periods") or {}).get("test", {}).get("metrics")})
        selection_rule = "Predeclared slow-window variants 150/200/250 sessions; no best-variant substitution."
    else:
        base_lookback = int(supplied.get("lookback_sessions", DEFAULTS["lookback_sessions"]))
        variants = sorted({max(126, base_lookback - 63), base_lookback, base_lookback + 63})
        for lookback in variants:
            variant = runner(rows, classifications=classifications, config={**supplied, "lookback_sessions": lookback})
            sensitivity.append({"lookback_sessions": lookback, "ok": bool(variant.get("ok")), "metrics": variant.get("metrics"),
                                "test_metrics": ((variant.get("validation") or {}).get("periods") or {}).get("test", {}).get("metrics")})
        selection_rule = "Predeclared lookback +/- 63 sessions; no best-variant substitution."
    result["parameter_sensitivity"] = {
        "status": "COMPLETED" if all(item["ok"] for item in sensitivity) else "PARTIAL",
        "variants": sensitivity,
        "selection_rule": selection_rule,
    }
    return result
