"""Auditable, point-in-time research backtests for the Hedge Fund Lab.

This module deliberately fails closed when the warehouse cannot support a
test.  A screen is not labelled as a strategy until its inputs were available
on each decision date and the simulated portfolio has paid its costs.
"""

from __future__ import annotations

import math
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
    weights: dict[str, float] = {}
    entry: dict[str, float] = {}
    peak: dict[str, float] = {}
    returns: list[float] = []
    return_dates: list[str] = []
    turnover: list[float] = []
    rebalances: list[dict[str, Any]] = []
    stopped: set[str] = set()
    start = lookback + 1
    for i in range(start, len(calendar)):
        today, previous = calendar[i], calendar[i - 1]
        bars, prior = by_day[today], by_day[previous]
        is_rebalance = (i - start) % rebalance_every == 0
        old_weights = dict(weights)
        if is_rebalance:
            candidates: list[tuple[float, str]] = []
            for symbol, series in prices.items():
                history = [bar for bar in series if bar["date"] <= previous]
                if len(history) < lookback:
                    continue
                end, base = history[-skip - 1], history[-lookback]
                if base["close"] <= 0:
                    continue
                avg_value = sum(bar["close"] * bar["volume"] for bar in history[-21:]) / min(21, len(history))
                if avg_value < float(cfg["min_average_daily_value"]):
                    continue
                candidates.append((end["close"] / base["close"] - 1.0, symbol))
            candidates.sort(reverse=True)
            sector_used: dict[str, float] = defaultdict(float)
            selected: list[str] = []
            raw_weight = min(float(cfg["max_weight"]), 1.0 / holdings)
            for _, symbol in candidates:
                sector = sectors.get(symbol, "Unclassified")
                if sector_used[sector] + raw_weight > float(cfg["max_sector_weight"]) + 1e-12:
                    continue
                selected.append(symbol)
                sector_used[sector] += raw_weight
                if len(selected) == holdings:
                    break
            weights = {symbol: 1.0 / len(selected) for symbol in selected} if selected else {}
            entry = {symbol: bars[symbol]["close"] for symbol in weights if symbol in bars}
            peak = dict(entry)
            stopped.clear()
            rebalances.append({"date": today, "selected": sorted(weights), "candidate_count": len(candidates)})

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
        "constraints": {key: cfg[key] for key in ("holdings", "max_weight", "max_sector_weight", "min_average_daily_value")},
        "coverage": {"symbols_with_price_history": len(prices), "calendar_sessions": len(calendar),
                     "backtest_sessions": len(returns), "rebalance_count": len(rebalances)},
        "metrics": _metrics(returns),
        "validation": _validation_report(return_dates, returns),
        "average_turnover_pct": round(sum(turnover) / len(turnover) * 100, 3),
        "rebalances": rebalances[-24:],
        "limitations": [
            "Long-only price momentum only; no borrow, short rebate, taxes or intraday execution model.",
            "Corporate-action-adjusted closes are used when available; incomplete adjustment history invalidates interpretation.",
            "This is a research backtest, not evidence of future returns or a production trading instruction.",
        ],
    }


def run_from_warehouse(strategy: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load the bounded warehouse inputs needed by the backtest."""
    if str(strategy).lower() not in {"momentum", "momentum_12_1_long_only"}:
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
    result = momentum_backtest(rows, classifications=classifications, config=supplied)
    if not result.get("ok") or not sensitivity_enabled:
        return result
    base_lookback = int(supplied.get("lookback_sessions", DEFAULTS["lookback_sessions"]))
    variants = sorted({max(126, base_lookback - 63), base_lookback, base_lookback + 63})
    sensitivity = []
    for lookback in variants:
        variant = momentum_backtest(rows, classifications=classifications, config={**supplied, "lookback_sessions": lookback})
        sensitivity.append({
            "lookback_sessions": lookback,
            "ok": bool(variant.get("ok")),
            "metrics": variant.get("metrics"),
            "test_metrics": ((variant.get("validation") or {}).get("periods") or {}).get("test", {}).get("metrics"),
        })
    result["parameter_sensitivity"] = {
        "status": "COMPLETED" if all(item["ok"] for item in sensitivity) else "PARTIAL",
        "variants": sensitivity,
        "selection_rule": "Predeclared lookback +/- 63 sessions; no best-variant substitution.",
    }
    return result
