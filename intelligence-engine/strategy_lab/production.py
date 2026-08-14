"""Phase 1 Strategy Lab engines over AGI's adjusted daily-price warehouse.

Outputs are research signals. Promotion and execution fail closed until the
validation registry contains the required point-in-time and out-of-sample evidence.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

VERSION = "strategy-lab-phase1-v1.0.0"
LIFECYCLE = ("DRAFT", "BACKTESTING", "VALIDATING", "PAPER", "OPERATIONAL", "SUSPENDED", "RETIRED")
COMMON_DATA = ["adjusted_daily_ohlcv", "liquidity", "corporate_actions"]

REGISTRY: dict[str, dict[str, Any]] = {
    "time_series_momentum": {
        "name": "Time-Series Momentum", "family": "TREND", "lifecycle": "BACKTESTING",
        "holding_period": "1-12 months", "overlap": "cross_sectional_momentum_v1",
        "overlap_note": "Different horizon and construction; medium-term absolute trend, not intraday cross-sectional leadership.",
        "formula": "0.15*z(R21)+0.25*z(R63)+0.25*z(R126)+0.35*z(R252), divided by realized volatility",
        "parameters": {"windows": [21, 63, 126, 252], "weights": [0.15, 0.25, 0.25, 0.35], "buy": 0.35, "sell": -0.35},
    },
    "trend_following": {
        "name": "Trend Following", "family": "TREND", "lifecycle": "BACKTESTING",
        "holding_period": "1-12 months", "overlap": None,
        "formula": "Price/SMA200, SMA50/SMA200, SMA200 slope, ADX and ATR",
        "parameters": {"fast_sma": 50, "slow_sma": 200, "slope_window": 20, "atr_window": 14, "stop_atr": 2.5},
    },
    "volatility_breakout": {
        "name": "Volatility Breakout", "family": "BREAKOUT", "lifecycle": "BACKTESTING",
        "holding_period": "2-12 weeks", "overlap": "opening_range_expansion_v1",
        "overlap_note": "Daily 20/55-session Donchian breakout; not Live Alpha's opening-range intraday breakout.",
        "formula": "Close versus prior 20/55-session high or low, confirmed by ATR regime and volume",
        "parameters": {"entry_windows": [20, 55], "exit_window": 20, "atr_window": 14, "volume_window": 20, "stop_atr": 2.0},
    },
    "mean_reversion": {
        "name": "Medium-Term Mean Reversion", "family": "MEAN_REVERSION", "lifecycle": "BACKTESTING",
        "holding_period": "5-30 sessions", "overlap": "intraday_mean_reversion_v1",
        "overlap_note": "Daily 20-session dislocation with 200-day trend and volatility filters; not intraday residual reversion.",
        "formula": "Z=(Close-SMA20)/SD20, gated by SMA200 trend, liquidity and volatility percentile",
        "parameters": {"mean_window": 20, "trend_window": 200, "entry_z": 2.0, "exit_z": 0.5, "atr_window": 14, "stop_atr": 2.0},
    },
}


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _warehouse_rows(limit: int = 500_000) -> list[dict[str, Any]]:
    from institutional_warehouse import store
    return store.all_rows("daily_market_history", limit=limit) or []


def _series(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, float | str]]]:
    grouped: dict[str, dict[str, dict[str, float | str]]] = defaultdict(dict)
    for row in rows:
        ticker = str(row.get("symbol") or row.get("ticker") or "").upper()
        day = str(row.get("date") or row.get("period") or "")[:10]
        close = _num(row.get("adjusted_close")) or _num(row.get("close"))
        if not ticker or len(day) != 10 or close is None or close <= 0:
            continue
        grouped[ticker][day] = {
            "date": day, "close": close,
            "high": _num(row.get("high")) or close,
            "low": _num(row.get("low")) or close,
            "volume": _num(row.get("volume")) or 0.0,
        }
    return {ticker: [days[d] for d in sorted(days)] for ticker, days in grouped.items()}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sd(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _atr(bars: list[dict[str, Any]], window: int = 14) -> float | None:
    if len(bars) < window + 1:
        return None
    true_ranges = []
    for previous, current in zip(bars[-window - 1:-1], bars[-window:]):
        true_ranges.append(max(float(current["high"]) - float(current["low"]), abs(float(current["high"]) - float(previous["close"])), abs(float(current["low"]) - float(previous["close"]))))
    return _mean(true_ranges)


def _liquid(bars: list[dict[str, Any]]) -> tuple[bool, float]:
    sample = bars[-20:]
    adv = _mean([float(b["close"]) * float(b["volume"]) for b in sample]) if sample else 0.0
    return adv >= 2_000_000, adv


def _base_signal(strategy_id: str, ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
    liquid, adv = _liquid(bars)
    return {
        "strategy_id": strategy_id, "strategy_version": VERSION, "ticker": ticker,
        "timestamp": bars[-1]["date"], "eligibility": "RESEARCH_ONLY", "trade_eligible": False,
        "data": {"source": "warehouse.daily_market_history", "observations": len(bars), "freshness": bars[-1]["date"],
                 "completeness": round(min(100.0, len(bars) / 252 * 100), 1), "pit_status": "PIT_LIMITED", "liquid": liquid, "average_daily_value": round(adv, 2)},
        "governance": {"lifecycle": REGISTRY[strategy_id]["lifecycle"], "decision": "DO_NOT_DEPLOY", "execution": "BLOCKED"},
    }


def _momentum(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(bars) < 253: return None
    out = _base_signal("time_series_momentum", ticker, bars)
    closes = [float(b["close"]) for b in bars]
    returns = {w: closes[-1] / closes[-w - 1] - 1 for w in (21, 63, 126, 252)}
    daily = [closes[i] / closes[i - 1] - 1 for i in range(max(1, len(closes) - 63), len(closes))]
    vol = _sd(daily) * math.sqrt(252)
    raw = sum(w * returns[n] for n, w in zip((21, 63, 126, 252), (0.15, 0.25, 0.25, 0.35)))
    score = raw / max(vol, 0.05)
    signal = "BUY" if score > .35 and returns[63] > 0 else "SELL" if score < -.35 and returns[63] < 0 else "HOLD"
    out.update(signal=signal, score=round(max(-100, min(100, score * 40)), 2), confidence="MEDIUM" if out["data"]["liquid"] else "LOW",
               entry=closes[-1], stop=None, target=None, expected_holding_period="1-12 months",
               factor_contributions={f"return_{n}d": round(v * 100, 3) for n, v in returns.items()} | {"realized_volatility_pct": round(vol * 100, 3), "risk_adjusted_momentum": round(score, 4)},
               reason_codes=["POSITIVE_ABSOLUTE_TREND" if signal == "BUY" else "NEGATIVE_ABSOLUTE_TREND" if signal == "SELL" else "NEUTRAL_TREND"],
               explanation={"main_driver": "Weighted medium-term absolute returns adjusted for realized volatility.", "contradictory_evidence": [], "limitations": ["Cross-sectional normalization and portfolio construction require a full dated universe."]})
    return out


def _trend(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(bars) < 220: return None
    out = _base_signal("trend_following", ticker, bars); closes = [float(b["close"]) for b in bars]
    sma20, sma50, sma100, sma200 = (_mean(closes[-n:]) for n in (20, 50, 100, 200))
    prior200 = _mean(closes[-220:-20]); slope = sma200 / prior200 - 1
    atr = _atr(bars); price = closes[-1]
    signal = "BUY" if price > sma200 and sma50 > sma200 and slope > 0 else "SELL" if price < sma200 and sma50 < sma200 else "HOLD"
    stop = price - 2.5 * atr if signal == "BUY" and atr else price + 2.5 * atr if signal == "SELL" and atr else None
    strength = 50 * (price / sma200 - 1) + 50 * (sma50 / sma200 - 1)
    out.update(signal=signal, score=round(max(-100, min(100, strength * 10)), 2), confidence="MEDIUM", entry=price, stop=round(stop, 2) if stop else None, target=None, expected_holding_period="1-12 months",
               factor_contributions={"sma20": round(sma20, 2), "sma50": round(sma50, 2), "sma100": round(sma100, 2), "sma200": round(sma200, 2), "sma200_slope_pct": round(slope * 100, 3), "atr14": round(atr, 3) if atr else None},
               reason_codes=["PRICE_ABOVE_SMA200", "SMA50_ABOVE_SMA200", "POSITIVE_SLOW_TREND"] if signal == "BUY" else ["NO_CONFIRMED_TREND"] if signal == "HOLD" else ["PRICE_BELOW_SMA200", "SMA50_BELOW_SMA200"],
               explanation={"main_driver": "Price and moving-average alignment with an explicitly recorded ATR stop multiple.", "contradictory_evidence": [], "limitations": ["ADX is withheld until high/low completeness is independently verified."]})
    return out


def _breakout(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(bars) < 56: return None
    out = _base_signal("volatility_breakout", ticker, bars); current = bars[-1]; previous = bars[:-1]
    hi20, hi55 = max(float(b["high"]) for b in previous[-20:]), max(float(b["high"]) for b in previous[-55:])
    lo20, lo55 = min(float(b["low"]) for b in previous[-20:]), min(float(b["low"]) for b in previous[-55:])
    atr = _atr(bars); volume_avg = _mean([float(b["volume"]) for b in previous[-20:]]); volume_ratio = float(current["volume"]) / volume_avg if volume_avg > 0 else None
    price = float(current["close"]); signal = "BUY" if price > hi55 and (volume_ratio or 0) >= 1 else "SELL" if price < lo20 else "HOLD"
    stop = price - 2 * atr if signal == "BUY" and atr else price + 2 * atr if signal == "SELL" and atr else None
    out.update(signal=signal, score=round(max(-100, min(100, (price / hi55 - 1) * 500)), 2), confidence="MEDIUM" if volume_ratio else "LOW", entry=price, stop=round(stop, 2) if stop else None, target=None, expected_holding_period="2-12 weeks",
               factor_contributions={"prior_high_20": round(hi20, 2), "prior_high_55": round(hi55, 2), "prior_low_20": round(lo20, 2), "prior_low_55": round(lo55, 2), "atr14": round(atr, 3) if atr else None, "volume_ratio": round(volume_ratio, 3) if volume_ratio else None},
               reason_codes=["DONCHIAN_55_BREAKOUT", "VOLUME_CONFIRMED"] if signal == "BUY" else ["DONCHIAN_20_EXIT"] if signal == "SELL" else ["INSIDE_DONCHIAN_CHANNEL"],
               explanation={"main_driver": "Close relative to prior Donchian bounds, with volume confirmation and ATR risk distance.", "contradictory_evidence": [], "limitations": ["Signal uses end-of-day confirmation; execution must occur no earlier than the next tradable session."]})
    return out


def _reversion(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(bars) < 220: return None
    out = _base_signal("mean_reversion", ticker, bars); closes = [float(b["close"]) for b in bars]; sample = closes[-20:]
    mean, sd, price = _mean(sample), _sd(sample), closes[-1]; z = (price - mean) / sd if sd > 0 else 0
    sma200 = _mean(closes[-200:]); prior200 = _mean(closes[-220:-20]); trend_positive = sma200 > prior200
    atr = _atr(bars); vol_pct = (atr / price * 100) if atr else None
    signal = "BUY" if z < -2 and trend_positive and out["data"]["liquid"] else "SELL" if z > 2 else "EXIT" if abs(z) < .5 else "HOLD"
    stop = price - 2 * atr if signal == "BUY" and atr else None
    out.update(signal=signal, score=round(max(-100, min(100, -z * 30)), 2), confidence="MEDIUM" if signal != "HOLD" else "LOW", entry=price, stop=round(stop, 2) if stop else None, target=round(mean, 2) if signal == "BUY" else None, expected_holding_period="5-30 sessions",
               factor_contributions={"z_score_20": round(z, 4), "mean_20": round(mean, 2), "std_20": round(sd, 3), "sma200": round(sma200, 2), "sma200_trend_positive": trend_positive, "atr_pct": round(vol_pct, 3) if vol_pct else None},
               reason_codes=["OVERSOLD_ZSCORE", "POSITIVE_LONG_TREND", "LIQUIDITY_PASSED"] if signal == "BUY" else ["MEAN_REVERSION_EXIT"] if signal == "EXIT" else ["NO_FILTERED_REVERSION_ENTRY"],
               explanation={"main_driver": "Twenty-session price dislocation, conditioned on the slow trend and liquidity.", "contradictory_evidence": ([] if trend_positive else ["Long-term trend is not positive."]), "limitations": ["Volatility-regime percentile requires a deeper verified ATR history before promotion."]})
    return out


CALCULATORS = {"time_series_momentum": _momentum, "trend_following": _trend, "volatility_breakout": _breakout, "mean_reversion": _reversion}


def health() -> dict[str, Any]:
    try:
        rows = _warehouse_rows(limit=1_000)
    except Exception as exc:
        return {"ok": False, "status": "DATA_UNAVAILABLE", "error": str(exc)[:160], "version": VERSION}
    return {"ok": True, "status": "RESEARCH_ONLY", "version": VERSION, "phase": 1, "strategies": len(REGISTRY), "warehouse_rows_sampled": len(rows), "execution_enabled": False, "promotion_authority": "strategy_validation_gates"}


def strategy(strategy_id: str) -> dict[str, Any]:
    item = REGISTRY.get(strategy_id)
    return {"ok": bool(item), "strategy_id": strategy_id, **(item or {"error": "unknown_strategy"}), "version": VERSION, "data_requirements": COMMON_DATA, "trade_eligible": False}


def scan(strategy_id: str, limit: int = 20) -> dict[str, Any]:
    calculator = CALCULATORS.get(strategy_id)
    if not calculator: return {"ok": False, "error": "unknown_strategy", "strategy_id": strategy_id}
    series = _series(_warehouse_rows())
    signals = [signal for ticker, bars in series.items() if (signal := calculator(ticker, bars)) is not None]
    priority = {"BUY": 4, "SELL": 3, "EXIT": 2, "HOLD": 1}
    signals.sort(key=lambda x: (priority.get(str(x.get("signal")), 0), abs(float(x.get("score") or 0))), reverse=True)
    return {"ok": True, "strategy": strategy(strategy_id), "as_of": max((s["timestamp"] for s in signals), default=None), "universe_with_sufficient_history": len(signals), "signals": signals[:max(1, min(limit, 100))], "trade_eligible_count": 0, "policy": "Research signal only; validation and execution gates remain blocked."}


def dashboard(limit: int = 5) -> dict[str, Any]:
    series = _series(_warehouse_rows())
    cards = []
    for key in REGISTRY:
        calculator = CALCULATORS[key]
        all_signals = [signal for ticker, bars in series.items() if (signal := calculator(ticker, bars)) is not None]
        priority = {"BUY": 4, "SELL": 3, "EXIT": 2, "HOLD": 1}
        all_signals.sort(key=lambda x: (priority.get(str(x.get("signal")), 0), abs(float(x.get("score") or 0))), reverse=True)
        rows = all_signals[:max(1, min(limit, 20))]
        cards.append({**strategy(key), "as_of": max((s["timestamp"] for s in all_signals), default=None), "universe": len(all_signals), "signal_count": len(rows), "signals": rows})
    return {"ok": True, "generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION, "admin_only": True, "research_only": True, "execution_enabled": False, "lifecycle": list(LIFECYCLE), "strategies": cards,
            "promotion_gates": ["sufficient_observations", "point_in_time_compliance", "costed_backtest", "positive_out_of_sample", "drawdown_limit", "parameter_stability", "survivorship_review"],
            "next_phases": {"phase_2": ["quality_value", "quality_momentum", "value_reversal", "fundamental_deterioration", "balance_sheet_risk"], "status": "NOT_IMPLEMENTED"}}


def backtest(strategy_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    if strategy_id != "time_series_momentum":
        return {"ok": False, "status": "DATA_BUILDING", "error": "strategy_specific_walk_forward_backtest_not_implemented", "strategy_id": strategy_id, "decision": "DO_NOT_DEPLOY"}
    from hedge_fund_lab.backtests import run_from_warehouse
    result = run_from_warehouse("momentum", config or {})
    return {**result, "strategy_lab_id": strategy_id, "validation": {"out_of_sample": "NOT_COMPLETED", "parameter_sensitivity": "NOT_COMPLETED", "survivorship": "SURVIVORSHIP_BIAS_RISK", "promotion": "DO_NOT_DEPLOY"}}
