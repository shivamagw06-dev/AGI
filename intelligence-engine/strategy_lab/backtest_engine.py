"""Auditable standardized backtesting with costs, capacity and OOS partitions."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from strategy_lab.execution import IndiaCashCostSchedule, estimate_trade_cost
from strategy_lab.portfolio import construct, risk_report
from strategy_lab.research import walk_forward_partitions


def _performance(returns: Sequence[float]) -> dict[str, Any]:
    if not returns:
        return {"cumulative_return": 0.0, "annualized_return": None, "volatility": None, "sharpe": None, "sortino": None, "max_drawdown": 0.0, "calmar": None, "hit_rate": None}
    nav = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        nav *= 1.0 + value
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1.0)
    annualized = nav ** (252.0 / len(returns)) - 1.0 if nav > 0 else -1.0
    volatility = statistics.stdev(returns) * math.sqrt(252.0) if len(returns) > 1 else None
    downside = [value for value in returns if value < 0]
    downside_vol = statistics.pstdev(downside) * math.sqrt(252.0) if len(downside) > 1 else None
    return {
        "cumulative_return": nav - 1.0,
        "annualized_return": annualized,
        "volatility": volatility,
        "sharpe": annualized / volatility if volatility else None,
        "sortino": annualized / downside_vol if downside_vol else None,
        "max_drawdown": drawdown,
        "calmar": annualized / abs(drawdown) if drawdown else None,
        "hit_rate": sum(value > 0 for value in returns) / len(returns),
    }


def run(
    observations: Iterable[Mapping[str, Any]],
    *,
    capital: float,
    schedule: IndiaCashCostSchedule,
    benchmark_returns: Mapping[str, float] | None = None,
    max_position_weight: float = 0.05,
    max_sector_weight: float = 0.25,
    max_adv_participation: float = 0.05,
    long_short: bool = False,
) -> dict[str, Any]:
    """Backtest precomputed point-in-time signals using next-session executions.

    Each observation must include signal_date, execution_date, exit_date,
    entry_price, exit_price, score, volatility and ADV. This explicit contract
    prevents the engine from silently using same-close information.
    """
    rows = [dict(row) for row in observations]
    by_signal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("execution_date")) <= str(row.get("signal_date")):
            raise ValueError("execution_must_follow_signal")
        if str(row.get("exit_date")) < str(row.get("execution_date")):
            raise ValueError("exit_before_entry")
        by_signal[str(row.get("signal_date"))].append(row)

    trades = []
    daily_returns: dict[str, float] = defaultdict(float)
    gross_turnover = 0.0
    costs_total = 0.0
    capacity = {str(amount): True for amount in (5e7, 1e8, 2.5e8, 5e8, 1e9)}
    for signal_date, cohort in sorted(by_signal.items()):
        portfolio = construct(
            cohort, capital=capital, max_position_weight=max_position_weight,
            max_sector_weight=max_sector_weight, max_adv_participation=max_adv_participation,
            long_short=long_short,
        )
        for position in portfolio["positions"]:
            entry = float(position.get("entry_price") or 0.0)
            exit_price = float(position.get("exit_price") or 0.0)
            if entry <= 0 or exit_price <= 0:
                continue
            weight = float(position["weight"])
            side = "BUY" if weight > 0 else "SELL"
            notional = abs(capital * weight)
            entry_cost = estimate_trade_cost(notional, side, adv=float(position.get("adv") or 0.0), schedule=schedule,
                                             quoted_spread_bps=float(position.get("spread_bps") or 0.0))
            exit_side = "SELL" if side == "BUY" else "BUY"
            exit_cost = estimate_trade_cost(notional, exit_side, adv=float(position.get("adv") or 0.0), schedule=schedule,
                                            quoted_spread_bps=float(position.get("spread_bps") or 0.0))
            gross_return = (exit_price / entry - 1.0) * (1.0 if weight > 0 else -1.0)
            cost_value = float(entry_cost.get("cost") or 0.0) + float(exit_cost.get("cost") or 0.0)
            net_return = gross_return - cost_value / notional
            contribution = abs(weight) * net_return
            daily_returns[str(position.get("exit_date"))] += contribution
            gross_turnover += 2.0 * abs(weight)
            costs_total += cost_value
            trades.append({
                "symbol": position.get("symbol") or position.get("company_id"),
                "signal_date": signal_date,
                "execution_date": position.get("execution_date"),
                "exit_date": position.get("exit_date"),
                "side": side,
                "weight": weight,
                "entry_price": entry,
                "exit_price": exit_price,
                "gross_return": gross_return,
                "net_return": net_return,
                "cost": cost_value,
                "entry_cost": entry_cost,
                "exit_cost": exit_cost,
            })
            adv = float(position.get("adv") or 0.0)
            for amount in list(capacity):
                if adv <= 0 or float(amount) * abs(weight) / adv > max_adv_participation:
                    capacity[amount] = False

    dated = sorted(daily_returns)
    returns = [daily_returns[day] for day in dated]
    benchmark = [float((benchmark_returns or {}).get(day, 0.0)) for day in dated]
    excess = [value - bench for value, bench in zip(returns, benchmark)]
    partitions = walk_forward_partitions(sorted(by_signal))
    partition_metrics = {}
    for name, dates in partitions.items():
        date_set = set(dates)
        sample = [float(trade["net_return"]) * abs(float(trade["weight"])) for trade in trades if trade["signal_date"] in date_set]
        partition_metrics[name] = _performance(sample)
    positions = [{"weight": trade["weight"], "sector": next((row.get("sector") for row in rows if (row.get("symbol") or row.get("company_id")) == trade["symbol"]), None),
                  "beta": next((row.get("beta") for row in rows if (row.get("symbol") or row.get("company_id")) == trade["symbol"]), 0.0),
                  "adv": next((row.get("adv") for row in rows if (row.get("symbol") or row.get("company_id")) == trade["symbol"]), 0.0),
                  "notional": capital * trade["weight"]} for trade in trades]
    return {
        "metrics": _performance(returns),
        "benchmark_metrics": _performance(benchmark),
        "excess_metrics": _performance(excess),
        "daily_returns": [{"date": day, "return": daily_returns[day], "benchmark_return": (benchmark_returns or {}).get(day)} for day in dated],
        "monthly_returns": _monthly_returns(daily_returns),
        "trades": trades,
        "positions": positions,
        "turnover": gross_turnover,
        "transaction_costs": costs_total,
        "capacity": {label: allowed for label, allowed in capacity.items()},
        "walk_forward": partition_metrics,
        "risk": risk_report(positions, portfolio_returns=returns),
        "cost_schedule_hash": schedule.schedule_hash,
        "claim": "historical_simulation_not_live_performance",
    }


def _monthly_returns(daily: Mapping[str, float]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for day, value in daily.items():
        grouped[str(day)[:7]].append(float(value))
    output = []
    for month, values in sorted(grouped.items()):
        compounded = 1.0
        for value in values:
            compounded *= 1.0 + value
        output.append({"month": month, "return": compounded - 1.0})
    return output
