"""Phase 1 Strategy Lab engines over AGI's adjusted daily-price warehouse.

Outputs are research signals. Promotion and execution fail closed until the
validation registry contains the required point-in-time and out-of-sample evidence.
"""

from __future__ import annotations

import math
import statistics
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .validation_registry import evaluate as evaluate_registry

VERSION = "strategy-lab-governance-v1.1.0"
LIFECYCLE = (
    "DRAFT", "IMPLEMENTED", "DATA_VALIDATED", "BACKTESTABLE",
    "RESEARCH_VALIDATED", "PAPER_ELIGIBLE", "PAPER_VALIDATED",
    "PRODUCTION_CANDIDATE", "EXECUTION_ELIGIBLE", "SUSPENDED", "RETIRED",
)
SIGNAL_STATUS = ("RESEARCH_ONLY", "BLOCKED", "PAPER_ELIGIBLE", "EXECUTION_ELIGIBLE")
COMMON_DATA = ["adjusted_daily_ohlcv", "liquidity", "corporate_actions"]
_CACHE_LOCK = threading.Lock()
_PRICE_CACHE: dict[str, Any] = {"at": 0.0, "rows": []}
_CACHE_TTL_SECONDS = 300

REGISTRY: dict[str, dict[str, Any]] = {
    "time_series_momentum": {
        "name": "Time-Series Momentum", "family": "TREND", "lifecycle": "IMPLEMENTED", "category": "IMPLEMENTED",
        "holding_period": "1-12 months", "data_mode": "EOD", "overlap": "cross_sectional_momentum_v1",
        "overlap_note": "Different horizon and construction; medium-term absolute trend, not intraday cross-sectional leadership.",
        "formula": "0.15*z(R21)+0.25*z(R63)+0.25*z(R126)+0.35*z(R252), divided by realized volatility",
        "parameters": {"windows": [21, 63, 126, 252], "weights": [0.15, 0.25, 0.25, 0.35], "buy": 0.35, "sell": -0.35},
    },
    "trend_following": {
        "name": "Trend Following", "family": "TREND", "lifecycle": "IMPLEMENTED", "category": "IMPLEMENTED",
        "holding_period": "1-12 months", "data_mode": "EOD", "overlap": None,
        "formula": "Price/SMA200, SMA50/SMA200, SMA200 slope, ADX and ATR",
        "parameters": {"fast_sma": 50, "slow_sma": 200, "slope_window": 20, "atr_window": 14, "stop_atr": 2.5},
    },
    "volatility_breakout": {
        "name": "Volatility Breakout", "family": "BREAKOUT", "lifecycle": "IMPLEMENTED", "category": "IMPLEMENTED",
        "holding_period": "2-12 weeks", "data_mode": "EOD", "overlap": "opening_range_expansion_v1",
        "overlap_note": "Daily 20/55-session Donchian breakout; not Live Alpha's opening-range intraday breakout.",
        "formula": "Close versus prior 20/55-session high or low, confirmed by ATR regime and volume",
        "parameters": {"entry_windows": [20, 55], "exit_window": 20, "atr_window": 14, "volume_window": 20, "stop_atr": 2.0},
    },
    "mean_reversion": {
        "name": "Medium-Term Mean Reversion", "family": "MEAN_REVERSION", "lifecycle": "IMPLEMENTED", "category": "IMPLEMENTED",
        "holding_period": "5-30 sessions", "data_mode": "EOD", "overlap": "intraday_mean_reversion_v1",
        "overlap_note": "Daily 20-session dislocation with 200-day trend and volatility filters; not intraday residual reversion.",
        "formula": "Z=(Close-SMA20)/SD20, gated by SMA200 trend, liquidity and volatility percentile",
        "parameters": {"mean_window": 20, "trend_window": 200, "entry_z": 2.0, "exit_z": 0.5, "atr_window": 14, "stop_atr": 2.0},
    },
    "cross_sectional_momentum": {
        "name": "Cross-Sectional Momentum", "family": "MOMENTUM", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "1-12 months", "data_mode": "EOD", "formula": "Percentile ranks of 1M/3M/6M/12M returns, volatility and sector-relative momentum",
        "parameters": {}, "blocked_by": ["PIT_DATA_MISSING", "BACKTEST_INSUFFICIENT"],
    },
    "quality_momentum": {
        "name": "Quality + Momentum", "family": "MULTI_FACTOR", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "3-18 months", "data_mode": "PIT + EOD", "formula": "wQ*Quality + wM*Momentum with explicit component attribution",
        "parameters": {}, "blocked_by": ["PIT_DATA_MISSING", "BACKTEST_INSUFFICIENT"],
    },
    "value_quality": {
        "name": "Value + Quality", "family": "MULTI_FACTOR", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "6-24 months", "data_mode": "PIT + EOD", "formula": "Historical valuation percentile combined with ROIC, FCF conversion and leverage quality",
        "parameters": {}, "blocked_by": ["PIT_DATA_MISSING", "BACKTEST_INSUFFICIENT"],
    },
    "accounting_quality": {
        "name": "Accounting Quality", "family": "FUNDAMENTAL", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "6-24 months", "data_mode": "PIT + EOD", "formula": "CFO/PAT, FCF/PAT, accruals, working-capital stress and exceptional-item dependence",
        "parameters": {}, "blocked_by": ["PIT_DATA_MISSING", "BACKTEST_INSUFFICIENT"],
    },
    "volatility_premia": {
        "name": "Volatility Premia", "family": "DERIVATIVES", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "1-12 weeks", "data_mode": "LIVE + DERIVATIVES", "formula": "Realized/implied volatility spread, skew, term structure, liquidity and open interest",
        "parameters": {}, "blocked_by": ["DERIVATIVES_DATA_MISSING", "BACKTEST_INSUFFICIENT"],
    },
    "sector_rotation": {
        "name": "Sector Rotation", "family": "ALLOCATION", "lifecycle": "DRAFT", "category": "DATA_BUILDING",
        "holding_period": "1-12 months", "data_mode": "EOD + MACRO", "formula": "Sector momentum, relative valuation, fundamental strength and macro sensitivity",
        "parameters": {}, "blocked_by": ["PIT_DATA_MISSING", "RISK_LIMIT"],
    },
    "event_strategies": {
        "name": "Event Strategies", "family": "EVENT", "lifecycle": "DRAFT", "category": "BLOCKED",
        "holding_period": "Event dependent", "data_mode": "PIT + EOD", "formula": "Timestamped abnormal and cumulative abnormal returns around classified events",
        "parameters": {}, "blocked_by": ["EVENT_TIMESTAMP_MISSING", "CORPORATE_ACTION_UNVERIFIED"],
    },
    "pairs_stat_arb": {
        "name": "Pairs / Statistical Arbitrage", "family": "STATISTICAL_ARBITRAGE", "lifecycle": "DRAFT", "category": "BLOCKED",
        "holding_period": "Days to months", "data_mode": "INTRADAY + EOD", "formula": "Cointegrated log-price spread, hedge ratio, residual z-score and half-life",
        "parameters": {}, "blocked_by": ["CORPORATE_ACTION_UNVERIFIED", "COST_FAILURE"],
    },
    "macro_equity": {
        "name": "Macro-to-Equity", "family": "MACRO", "lifecycle": "DRAFT", "category": "BLOCKED",
        "holding_period": "1-12 months", "data_mode": "PIT + EOD", "formula": "Rolling sector sensitivities to rates, INR, oil, inflation, liquidity and credit",
        "parameters": {}, "blocked_by": ["MACRO_VINTAGE_MISSING", "PIT_DATA_MISSING"],
    },
    "composite_research": {
        "name": "Composite Research Strategy", "family": "COMPOSITE", "lifecycle": "DRAFT", "category": "BLOCKED",
        "holding_period": "Model dependent", "data_mode": "MULTI-MODE", "formula": "Only independently validated quality, value, growth, momentum, risk, macro and event components",
        "parameters": {}, "blocked_by": ["COMPONENT_VALIDATION_INSUFFICIENT", "BACKTEST_INSUFFICIENT"],
    },
}


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _warehouse_rows(limit: int = 800_000) -> list[dict[str, Any]]:
    """Read raw immutable prices without the expensive cell-override overlay.

    Strategy inputs are append-only market observations. Reading them through
    ``store.all_rows`` performs override lookups for every page and made a
    full-universe scan exceed Render's request window. This bounded projection
    keeps only the latest 300 sessions per symbol and is cached across engines.
    """
    now = time.monotonic()
    cached = _PRICE_CACHE.get("rows") or []
    if cached and now - float(_PRICE_CACHE.get("at") or 0) < _CACHE_TTL_SECONDS:
        return cached[:limit]
    with _CACHE_LOCK:
        cached = _PRICE_CACHE.get("rows") or []
        if cached and time.monotonic() - float(_PRICE_CACHE.get("at") or 0) < _CACHE_TTL_SECONDS:
            return cached[:limit]
        from institutional_warehouse import db
        from hedge_fund_lab.scanner import _universe

        covered = sorted(
            _universe(),
            key=lambda row: float(row.get("market_cap") or 0),
            reverse=True,
        )
        symbols = [str(row.get("ticker") or "").upper() for row in covered[:200]]
        symbols = [symbol for symbol in symbols if symbol]
        if not symbols:
            return []
        table = db.physical_table("daily_market_history")
        marks = ",".join("?" for _ in symbols)
        rows = db.query(
            f'''SELECT symbol, date, open, high, low, close, adjusted_close, volume
                FROM {table}
                WHERE COALESCE(sys_published, 1) = 1
                  AND symbol IN ({marks})
                ORDER BY symbol, date DESC''',
            tuple(symbols),
        )
        # Retain only the latest 300 sessions without asking SQLite to rank the
        # whole warehouse. The selected universe is capped at 200 liquid names.
        counts: dict[str, int] = defaultdict(int)
        bounded = []
        for row in rows:
            symbol = str(row.get("symbol") or "")
            if counts[symbol] >= 300:
                continue
            counts[symbol] += 1
            bounded.append(row)
        rows = sorted(bounded, key=lambda row: (str(row.get("symbol") or ""), str(row.get("date") or "")))
        _PRICE_CACHE.update({"at": time.monotonic(), "rows": rows})
        return rows[:limit]


def _expected_completed_session(now: datetime | None = None) -> str:
    local = now.astimezone(ZoneInfo("Asia/Kolkata")) if now else datetime.now(ZoneInfo("Asia/Kolkata"))
    candidate = local.date() if (local.hour, local.minute) >= (16, 0) else local.date() - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate.isoformat()


def _series_snapshot(rows: list[dict[str, Any]], expected_session: str | None = None) -> tuple[dict[str, list[dict[str, float | str]]], dict[str, Any]]:
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
    # A current intraday candle may exist for only part of the universe. Select
    # the newest session shared by at least 80% of the best-covered date, then
    # exclude companies missing that completed session. This prevents mixed-date
    # rankings and fails closed on stale symbols such as an unrefreshed daily bar.
    coverage: dict[str, int] = defaultdict(int)
    for days in grouped.values():
        for day in days:
            coverage[day] += 1
    peak = max(coverage.values(), default=0)
    threshold = max(1, math.ceil(peak * 0.80))
    eligible_dates = [day for day, count in coverage.items() if count >= threshold]
    common_observed_session = max(eligible_dates, default=None)
    completed_session = expected_session or _expected_completed_session()
    series: dict[str, list[dict[str, float | str]]] = {}
    stale: list[str] = []
    for ticker, days in grouped.items():
        if not completed_session or completed_session not in days:
            stale.append(ticker)
            continue
        series[ticker] = [days[day] for day in sorted(days) if day <= completed_session]
    return series, {
        "latest_completed_session": completed_session,
        "common_observed_session": common_observed_session,
        "session_coverage": coverage.get(completed_session, 0) if completed_session else 0,
        "coverage_threshold": threshold,
        "session_status": "PASS" if coverage.get(completed_session, 0) >= threshold else "FAIL",
        "exchange_calendar_status": "WEEKDAY_RULE_ONLY",
        "mixed_session_blocked": len(stale),
        "stale_tickers": sorted(stale),
    }


def _series(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, float | str]]]:
    return _series_snapshot(rows)[0]


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
    reason_codes = ["PIT_DATA_MISSING", "CORPORATE_ACTION_UNVERIFIED", "BACKTEST_INSUFFICIENT", "COST_FAILURE", "RISK_LIMIT"]
    if not liquid:
        reason_codes.append("LOW_LIQUIDITY")
    return {
        "strategy_id": strategy_id, "strategy_version": VERSION, "ticker": ticker,
        "timestamp": bars[-1]["date"], "signal_session": bars[-1]["date"], "eligibility": "BLOCKED", "trade_eligible": False,
        "data": {"source": "warehouse.daily_market_history", "observations": len(bars), "freshness": bars[-1]["date"],
                 "freshness_status": "PASS", "completed_session": True,
                 "completeness": round(min(100.0, len(bars) / 252 * 100), 1), "pit_status": "PIT_LIMITED", "liquid": liquid,
                 "liquidity_status": "PASS" if liquid else "FAIL", "corporate_action_status": "UNVERIFIED",
                 "average_daily_value": round(adv, 2)},
        "prices": {"signal_price": bars[-1]["close"], "signal_session": bars[-1]["date"],
                   "latest_completed_close": bars[-1]["close"], "latest_completed_session": bars[-1]["date"],
                   "live_price": None, "live_price_age_seconds": None, "live_source": "NOT_CONNECTED"},
        "validation": {"data": "PARTIAL", "pit": "FAIL", "liquidity": "PASS" if liquid else "FAIL",
                       "corporate_actions": "FAIL", "backtest": "FAIL", "costs": "FAIL", "out_of_sample": "FAIL",
                       "risk": "FAIL", "paper": "FAIL"},
        "reason_codes": reason_codes,
        "governance": {"lifecycle": REGISTRY[strategy_id]["lifecycle"], "signal_status": "BLOCKED",
                       "decision": "DO_NOT_DEPLOY", "execution": "BLOCKED", "next_eligible_status": "RESEARCH_ONLY"},
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


def _registry_decision(strategy_id: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    item = REGISTRY.get(strategy_id) or {}
    implemented = strategy_id in CALCULATORS
    session = session or {}
    session_passed = session.get("session_status") == "PASS"
    evidence = {
        "implementation": {
            "status": "PASSED" if implemented else "MISSING",
            "source": "strategy_lab.calculator_registry",
            "detail": "Deterministic calculator is registered." if implemented else "No calculator is registered.",
        },
        "data_freshness": {
            "status": "PASSED" if session_passed else "MISSING",
            "observed_at": session.get("latest_completed_session"),
            "source": "warehouse.daily_market_history",
            "detail": session.get("session_status") or "No session receipt supplied.",
        },
        "data_completeness": {
            "status": "PASSED" if session_passed else "MISSING",
            "observed_at": session.get("latest_completed_session"),
            "source": "strategy_lab.common_session_gate",
            "detail": {"coverage": session.get("session_coverage"), "threshold": session.get("coverage_threshold")},
        },
        "point_in_time": {"status": "PARTIAL", "source": "warehouse", "detail": "Annual fundamentals remain PIT limited."},
        "corporate_actions": {"status": "MISSING", "source": "warehouse", "detail": "Independent adjustment receipt not recorded."},
    }
    from .registry_store import load_latest_evidence
    durable_evidence = load_latest_evidence().get(strategy_id, {})
    for gate in ("backtest", "out_of_sample", "transaction_costs", "liquidity_capacity", "risk", "walk_forward_paper"):
        if gate in durable_evidence:
            evidence[gate] = durable_evidence[gate]
    requested = "OPERATIONAL" if implemented else "EXPERIMENTAL"
    health = "HEALTHY" if session_passed else "DEGRADED" if not session else "STALE"
    reason = "Latest completed session and common-universe coverage passed." if session_passed else "Current session evidence is unavailable or incomplete."
    return evaluate_registry(
        strategy_id,
        requested_lifecycle=requested,
        evidence=evidence,
        health=health,
        health_reason=reason,
        allowed_use="Mathematical research and candidate prioritisation" if implemented else "Methodology design only",
    )


def _govern_signal(signal: dict[str, Any]) -> dict[str, Any]:
    factor_reasons = list(signal.get("reason_codes") or [])
    gate_reasons = ["PIT_DATA_MISSING", "CORPORATE_ACTION_UNVERIFIED", "BACKTEST_INSUFFICIENT", "COST_FAILURE", "RISK_LIMIT"]
    if not signal.get("data", {}).get("liquid"):
        gate_reasons.append("LOW_LIQUIDITY")
    signal["reason_codes"] = list(dict.fromkeys(factor_reasons + gate_reasons))
    direction = {"BUY": "LONG", "SELL": "SHORT", "EXIT": "FLAT", "HOLD": "NEUTRAL"}.get(str(signal.get("signal")), "NEUTRAL")
    signal.update(research_direction=direction, signal_strength=abs(float(signal.get("score") or 0)), eligibility="BLOCKED", trade_eligible=False)
    signal.setdefault("governance", {}).update(signal_status="BLOCKED", decision="DO_NOT_DEPLOY", execution="BLOCKED")
    return signal


def health() -> dict[str, Any]:
    try:
        from hedge_fund_lab.scanner import universe_meta
        warehouse = universe_meta()
    except Exception as exc:
        return {"ok": False, "status": "DATA_UNAVAILABLE", "error": str(exc)[:160], "version": VERSION}
    from .registry_store import table_health
    return {"ok": True, "status": "RESEARCH_ONLY", "version": VERSION, "phase": 2, "strategies": len(REGISTRY), "warehouse_universe": warehouse.get("count", 0), "strategy_universe": "top_200_by_market_cap", "price_cache_ttl_seconds": _CACHE_TTL_SECONDS, "execution_enabled": False, "promotion_authority": "VALIDATION_REGISTRY_ONLY", "validation_registry_store": table_health()}


def strategy(strategy_id: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    item = REGISTRY.get(strategy_id)
    operational = strategy_id in CALCULATORS
    return {"ok": bool(item), "strategy_id": strategy_id, **(item or {"error": "unknown_strategy"}), "version": VERSION,
            "data_requirements": (item or {}).get("data_requirements", COMMON_DATA), "calculator_available": operational,
            "signal_status": "BLOCKED", "trade_eligible": False, "execution_eligible": False,
            "validation_registry": _registry_decision(strategy_id, session)}


def scan(strategy_id: str, limit: int = 20) -> dict[str, Any]:
    calculator = CALCULATORS.get(strategy_id)
    if not calculator:
        item = REGISTRY.get(strategy_id)
        return {"ok": bool(item), "status": "BLOCKED", "error": "strategy_not_implemented" if item else "unknown_strategy",
                "strategy": strategy(strategy_id), "strategy_id": strategy_id, "signals": [],
                "reason_codes": list((item or {}).get("blocked_by") or ["STRATEGY_NOT_IMPLEMENTED"]), "decision": "DO_NOT_DEPLOY"}
    series, session = _series_snapshot(_warehouse_rows())
    signals = [_govern_signal(signal) for ticker, bars in series.items() if (signal := calculator(ticker, bars)) is not None]
    priority = {"BUY": 4, "SELL": 3, "EXIT": 2, "HOLD": 1}
    signals.sort(key=lambda x: (priority.get(str(x.get("signal")), 0), abs(float(x.get("score") or 0))), reverse=True)
    return {"ok": True, "strategy": strategy(strategy_id, session), "as_of": session.get("latest_completed_session"), "session_health": session,
            "universe_with_sufficient_history": len(signals), "signals": signals[:max(1, min(limit, 100))], "trade_eligible_count": 0,
            "policy": "Mathematical research output only; PIT, corporate-action, backtest, cost, risk and paper gates remain blocked."}


def dashboard(limit: int = 5) -> dict[str, Any]:
    series, session = _series_snapshot(_warehouse_rows())
    cards = []
    for key in REGISTRY:
        calculator = CALCULATORS.get(key)
        if not calculator:
            cards.append({**strategy(key, session), "as_of": session.get("latest_completed_session"), "universe": 0, "signal_count": 0,
                          "signals": [], "reason_codes": list(REGISTRY[key].get("blocked_by") or [])})
            continue
        all_signals = [_govern_signal(signal) for ticker, bars in series.items() if (signal := calculator(ticker, bars)) is not None]
        priority = {"BUY": 4, "SELL": 3, "EXIT": 2, "HOLD": 1}
        all_signals.sort(key=lambda x: (priority.get(str(x.get("signal")), 0), abs(float(x.get("score") or 0))), reverse=True)
        rows = all_signals[:max(1, min(limit, 20))]
        cards.append({**strategy(key, session), "as_of": max((s["timestamp"] for s in all_signals), default=None), "universe": len(all_signals), "signal_count": len(rows), "signals": rows})
    from .registry_store import persist_decisions
    persistence = persist_decisions(cards)
    return {"ok": True, "generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION, "admin_only": True, "research_only": True, "execution_enabled": False,
            "global_execution_status": "BLOCKED", "lifecycle": list(LIFECYCLE), "signal_statuses": list(SIGNAL_STATUS), "session_health": session, "strategies": cards,
            "validation_registry": {"authority": "VALIDATION_REGISTRY", "version": "strategy-validation-registry-v2.0.0", "execution_allowed": 0, "persistence": persistence},
            "promotion_gates": ["sufficient_observations", "point_in_time_compliance", "costed_backtest", "positive_out_of_sample", "drawdown_limit", "parameter_stability", "survivorship_review"],
            "builder_contract": {"fields": ["universe", "data_fields", "transformations", "factors", "weights", "entry_rule", "exit_rule", "risk_rule", "liquidity_rule", "cost_assumptions"],
                                 "save_status": "DRAFT", "self_promotion_allowed": False, "arbitrary_code_allowed": False},
            "governance_statements": ["A mathematical signal is not an investment strategy.", "A backtested strategy is not a validated strategy.", "A validated strategy is not automatically executable."]}


def backtest(strategy_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    if strategy_id != "time_series_momentum":
        return {"ok": False, "status": "DATA_BUILDING", "error": "strategy_specific_walk_forward_backtest_not_implemented", "strategy_id": strategy_id, "decision": "DO_NOT_DEPLOY"}
    from hedge_fund_lab.backtests import run_from_warehouse
    result = run_from_warehouse("momentum", config or {})
    validation = result.get("validation") or {}
    completed = result.get("ok") is True and validation.get("status") == "COMPLETED"
    observed_at = (validation.get("periods") or {}).get("test", {}).get("end")
    evidence = {
        "backtest": {
            "status": "PASSED" if completed else "FAILED",
            "observed_at": observed_at,
            "source": "hedge_fund_lab.backtests",
            "source_version": result.get("model_version"),
            "detail": {"metrics": result.get("metrics"), "coverage": result.get("coverage"), "lookahead_check": validation.get("lookahead_check"), "parameter_sensitivity": result.get("parameter_sensitivity")},
            "limitations": result.get("limitations") or [],
        },
        "out_of_sample": {
            "status": "PASSED" if completed and validation.get("out_of_sample_observations", 0) >= 21 else "FAILED",
            "observed_at": observed_at,
            "source": "hedge_fund_lab.backtests",
            "source_version": result.get("model_version"),
            "detail": (validation.get("periods") or {}).get("test"),
        },
        "transaction_costs": {
            "status": "PASSED" if completed and validation.get("costs_included") else "FAILED",
            "observed_at": observed_at,
            "source": "hedge_fund_lab.backtests",
            "source_version": result.get("model_version"),
            "detail": result.get("execution"),
        },
        "liquidity_capacity": {
            "status": "PARTIAL" if completed else "FAILED",
            "observed_at": observed_at,
            "source": "hedge_fund_lab.backtests",
            "source_version": result.get("model_version"),
            "detail": {"minimum_average_daily_value": (result.get("constraints") or {}).get("min_average_daily_value"), "capacity_model": "NOT_COMPLETED"},
        },
        "risk": {
            "status": "PARTIAL" if completed else "FAILED",
            "observed_at": observed_at,
            "source": "hedge_fund_lab.backtests",
            "source_version": result.get("model_version"),
            "detail": {"max_drawdown_pct": (result.get("metrics") or {}).get("max_drawdown_pct"), "approved_limit": None},
        },
    }
    from .registry_store import append_validation_evidence
    persistence = append_validation_evidence(strategy_id, VERSION, evidence)
    return {**result, "strategy_lab_id": strategy_id, "validation": {**validation, "parameter_sensitivity": (result.get("parameter_sensitivity") or {}).get("status", "NOT_COMPLETED"), "survivorship": "SURVIVORSHIP_BIAS_RISK", "promotion": "DO_NOT_DEPLOY"}, "registry_evidence": evidence, "persistence": persistence}
