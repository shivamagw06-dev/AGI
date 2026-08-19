"""Intraday-native strategies: live signal joined to historical risk and liquidity.

The five Live Alpha engines have been emitting signals that only one consumer
reads — the `live_alpha` confluence scanner, which treats every engine as one
undifferentiated confirmation flag. As of 2026-08-19 that produced three
qualifying symbols out of a 2,369 name universe and touched one row in a
ten-row research queue.

This module gives three of those engines a strategy of their own. Each pairs a
live signal with the historical context needed to size it:

* Opening-range breakout      <- opening_range_expansion_v1  + ATR, ADV
* Intraday mean reversion     <- intraday_mean_reversion_v1  + ATR, beta
* Volume / liquidity anomaly  <- volume_liquidity_anomaly_v1 + ADV baselines

Nothing here is a recommendation and nothing is validated. Every row carries
the arithmetic that produced it so a reader can check the number rather than
trust it. Sizing is expressed as a target weight, never as an order.
"""

from __future__ import annotations

import math
import os
from datetime import date
from typing import Any, Optional

from .live_alpha_bridge import ENGINE_LABELS, fetch_live_alpha_rows, signed_score

# Portfolio construction constants. Overridable so a caller can explore the
# sensitivity of position size without redeploying.
VOL_TARGET = float(os.getenv("HFL_VOL_TARGET", "0.12"))          # annualised
TRADING_DAYS = 252
MAX_WEIGHT = float(os.getenv("HFL_MAX_WEIGHT", "0.10"))          # per name
ADV_PARTICIPATION = float(os.getenv("HFL_ADV_PARTICIPATION", "0.10"))
PORTFOLIO_CAPITAL = float(os.getenv("HFL_PORTFOLIO_CAPITAL", "1000000000"))  # INR 100cr
HOLDINGS = int(os.getenv("HFL_HOLDINGS", "20"))
ATR_STOP_MULTIPLE = float(os.getenv("HFL_ATR_STOP", "2.0"))

POLICY = "Research observations only — no buy, sell, price target or order."


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def _risk_and_liquidity() -> tuple[dict[str, dict], dict[str, dict]]:
    """Latest per-symbol risk metrics and liquidity from the vendor tabs.

    These are populated by financial_warehouse_completion.vendor_exports:
    beta 1M/3M/1Y/3Y and ATR for ~3,200 symbols, 3-month ADV for ~2,900.
    Missing coverage is reported per row rather than silently defaulted, since
    a position sized without beta or ADV is not a position anyone should hold.
    """
    risk: dict[str, dict] = {}
    liq: dict[str, dict] = {}
    try:
        from institutional_warehouse import store

        for row in store.all_rows("vendor_risk_metrics", limit=8000) or []:
            sym = str(row.get("symbol") or "").upper()
            if sym and sym not in risk:
                risk[sym] = row
        for row in store.all_rows("vendor_liquidity", limit=8000) or []:
            sym = str(row.get("symbol") or "").upper()
            if sym and sym not in liq:
                liq[sym] = row
    except Exception:
        # The strategies still run without them; every row will say so.
        pass
    return risk, liq


def annualised_vol(atr: Optional[float], price: Optional[float]) -> Optional[float]:
    """sigma_hat = (ATR / P) * sqrt(252).

    ATR is used rather than close-to-close standard deviation because it
    incorporates gaps, which is what an intraday strategy is exposed to.
    """
    if not atr or not price or price <= 0:
        return None
    return (atr / price) * math.sqrt(TRADING_DAYS)


def vol_target_weight(sigma: Optional[float], n: int = HOLDINGS) -> Optional[float]:
    """w_i = sigma_target / (sigma_hat_i * sqrt(N)).

    Equalises risk contribution so one volatile name cannot dominate the book.
    """
    if not sigma or sigma <= 0 or n <= 0:
        return None
    return VOL_TARGET / (sigma * math.sqrt(n))


def adv_cap(adv_shares_mn: Optional[float], price: Optional[float],
            capital: float = PORTFOLIO_CAPITAL) -> Optional[float]:
    """w_i <= alpha * ADV_value / C.

    Capital IQ reports ADV in millions of shares, so it is converted to traded
    value before the participation limit is applied. Without this a screen
    returns names that cannot actually be bought at size.
    """
    if not adv_shares_mn or not price or capital <= 0:
        return None
    adv_value = adv_shares_mn * 1e6 * price
    return (ADV_PARTICIPATION * adv_value) / capital


def size_position(*, price: Optional[float], atr: Optional[float],
                  adv_shares_mn: Optional[float], n: int = HOLDINGS) -> dict[str, Any]:
    """Full sizing chain, with every intermediate exposed."""
    sigma = annualised_vol(atr, price)
    raw = vol_target_weight(sigma, n)
    cap_liq = adv_cap(adv_shares_mn, price)
    limits = [w for w in (raw, cap_liq, MAX_WEIGHT) if w is not None]
    final = min(limits) if limits else None
    binding = None
    if final is not None:
        if raw is not None and abs(final - raw) < 1e-12:
            binding = "volatility_target"
        elif cap_liq is not None and abs(final - cap_liq) < 1e-12:
            binding = "liquidity"
        else:
            binding = "max_weight"
    # Notional is derived from the *published* weight, not the raw one, so a
    # reader multiplying the displayed weight by capital reproduces the
    # displayed notional exactly.
    shown_weight = round(final, 5) if final is not None else None
    return {
        "annualised_vol": round(sigma, 4) if sigma is not None else None,
        "vol_target_weight": round(raw, 5) if raw is not None else None,
        "liquidity_cap_weight": round(cap_liq, 5) if cap_liq is not None else None,
        "max_weight": MAX_WEIGHT,
        "target_weight": shown_weight,
        "binding_constraint": binding,
        "notional_inr": round(shown_weight * PORTFOLIO_CAPITAL) if shown_weight is not None else None,
    }


def _coverage(risk_row: Optional[dict], liq_row: Optional[dict]) -> dict[str, Any]:
    missing = []
    if not risk_row or _num(risk_row.get("atr")) is None:
        missing.append("atr")
    if not risk_row or _num(risk_row.get("beta_1y")) is None:
        missing.append("beta")
    if not liq_row or _num(liq_row.get("adv_3m")) is None:
        missing.append("adv")
    return {
        "complete": not missing,
        "missing": missing,
        "sizeable": "atr" not in missing and "adv" not in missing,
    }


def _base_row(sig: dict[str, Any], risk_row: Optional[dict], liq_row: Optional[dict]) -> dict[str, Any]:
    price = _num((sig.get("factor_values") or {}).get("last_price")) if isinstance(sig.get("factor_values"), dict) else None
    if price is None and risk_row:
        # SMA50 is a poor proxy for last price but keeps sizing expressible when
        # the signal payload omits it; flagged so it is never mistaken for a quote.
        price = _num(risk_row.get("sma50"))
        price_source = "sma50_proxy" if price is not None else None
    else:
        price_source = "live_signal" if price is not None else None

    atr = _num(risk_row.get("atr")) if risk_row else None
    adv = _num(liq_row.get("adv_3m")) if liq_row else None
    sizing = size_position(price=price, atr=atr, adv_shares_mn=adv)

    return {
        "ticker": sig.get("symbol"),
        "sector": sig.get("sector"),
        "direction": sig.get("direction"),
        "signal_quality": _num(sig.get("signal_quality_score")),
        "alpha_z": _num(sig.get("alpha_z")),
        "signed_score": round(signed_score(sig), 2),
        "engine": ENGINE_LABELS.get(sig.get("engine"), sig.get("engine")),
        "as_of": sig.get("as_of"),
        "price": round(price, 2) if price is not None else None,
        "price_source": price_source,
        "atr": round(atr, 2) if atr is not None else None,
        "beta_1y": _num(risk_row.get("beta_1y")) if risk_row else None,
        "adv_3m_shares_mn": adv,
        "adv_3m_value_inr": round(adv * 1e6 * price) if (adv and price) else None,
        "sizing": sizing,
        "coverage": _coverage(risk_row, liq_row),
        "policy": POLICY,
    }


def _engine_rows(engine: str, limit: int) -> list[dict[str, Any]]:
    payload = fetch_live_alpha_rows(limit=400)
    if not payload.get("ok"):
        return []
    risk, liq = _risk_and_liquidity()
    out: list[dict[str, Any]] = []
    for row in payload.get("rows") or []:
        sig = (row.get("engines") or {}).get(engine)
        if not sig:
            continue
        sym = str(sig.get("symbol") or row.get("symbol") or row.get("ticker") or "").upper()
        if not sym:
            continue
        sig = {**sig, "symbol": sym, "engine": engine,
               "sector": sig.get("sector") or row.get("sector")}
        out.append(_base_row(sig, risk.get(sym), liq.get(sym)))
    out.sort(key=lambda r: -(abs(r.get("signed_score") or 0)))
    return out[:limit]


# ---------------------------------------------------------------- strategies

def scan_opening_range_breakout(limit: int = 20) -> dict[str, Any]:
    rows = _engine_rows("opening_range_expansion_v1", limit)
    for row in rows:
        atr, price = row.get("atr"), row.get("price")
        if atr and price:
            long_side = str(row.get("direction") or "").lower().startswith("pos")
            stop = price - ATR_STOP_MULTIPLE * atr if long_side else price + ATR_STOP_MULTIPLE * atr
            row["stop"] = round(stop, 2)
            row["stop_distance_pct"] = round(100 * ATR_STOP_MULTIPLE * atr / price, 2)
        row["why"] = (
            f"{row['engine']} flagged a {row.get('direction')} opening-range expansion with "
            f"quality {row.get('signal_quality')}. "
            + (f"A {ATR_STOP_MULTIPLE}x ATR stop sits {row.get('stop_distance_pct')}% away. "
               if row.get("stop_distance_pct") else "ATR is unavailable, so no stop can be placed. ")
            + ("Position size is limited by " + str(row["sizing"].get("binding_constraint")).replace("_", " ") + "."
               if row["sizing"].get("target_weight") else "Not sizeable: missing "
               + ", ".join(row["coverage"]["missing"]) + ".")
        )
    return {
        "ok": True, "strategy": "opening_range_breakout",
        "label": "Opening-Range Breakout",
        "engine": ENGINE_LABELS["opening_range_expansion_v1"],
        "horizon": "Intraday to a few sessions",
        "edge": "Expansion out of the opening range persists when it clears the day's true range.",
        "question": "Is this expansion real, or noise inside the normal range?",
        "results": rows, "count": len(rows), "policy": POLICY,
    }


def scan_intraday_reversion(limit: int = 20) -> dict[str, Any]:
    rows = _engine_rows("intraday_mean_reversion_v1", limit)
    for row in rows:
        atr, price = row.get("atr"), row.get("price")
        if atr and price:
            row["band_pct"] = round(100 * atr / price, 2)
        beta = row.get("beta_1y")
        row["market_hedge_ratio"] = round(beta, 2) if beta is not None else None
        row["why"] = (
            f"{row['engine']} flagged a {row.get('direction')} intraday dislocation, quality "
            f"{row.get('signal_quality')}. "
            + (f"One ATR is {row.get('band_pct')}% of price, which frames the reversion band. "
               if row.get("band_pct") else "")
            + (f"Beta {beta} sets the hedge ratio if the position is run market-neutral."
               if beta is not None else "Beta is unavailable, so this cannot be hedged to zero market exposure.")
        )
    return {
        "ok": True, "strategy": "intraday_reversion",
        "label": "Intraday Mean Reversion",
        "engine": ENGINE_LABELS["intraday_mean_reversion_v1"],
        "horizon": "Hours to days",
        "edge": "Short-horizon dislocation from a stable intraday mean.",
        "question": "Is the mean stable, or has the level genuinely reset?",
        "results": rows, "count": len(rows), "policy": POLICY,
    }


def scan_flow_anomaly(limit: int = 20) -> dict[str, Any]:
    rows = _engine_rows("volume_liquidity_anomaly_v1", limit)
    for row in rows:
        adv_v = row.get("adv_3m_value_inr")
        row["adv_3m_value_cr"] = round(adv_v / 1e7, 2) if adv_v else None
        row["why"] = (
            f"{row['engine']} flagged unusual volume against its baseline, quality "
            f"{row.get('signal_quality')}, direction {row.get('direction')}. "
            + (f"Average daily value is Rs {row.get('adv_3m_value_cr')} cr, so a "
               f"{int(ADV_PARTICIPATION*100)}% participation cap allows "
               f"{row['sizing'].get('target_weight')} of capital."
               if row.get("adv_3m_value_cr") and row["sizing"].get("target_weight")
               else "Average daily value is unavailable, so participation cannot be bounded.")
        )
    return {
        "ok": True, "strategy": "flow_anomaly",
        "label": "Volume / Liquidity Anomaly",
        "engine": ENGINE_LABELS["volume_liquidity_anomaly_v1"],
        "horizon": "Intraday to a week",
        "edge": "Volume dislocated from its own baseline often precedes a directional move.",
        "question": "Is this accumulation, distribution, or a single print?",
        "results": rows, "count": len(rows), "policy": POLICY,
    }


LIVE_STRATEGIES = {
    "opening_range_breakout": ("Opening-Range Breakout", scan_opening_range_breakout),
    "intraday_reversion": ("Intraday Mean Reversion", scan_intraday_reversion),
    "flow_anomaly": ("Volume / Liquidity Anomaly", scan_flow_anomaly),
}


def board(limit: int = 12) -> dict[str, Any]:
    """All three strategies plus the sizing constants they share."""
    cards = []
    for key, (label, fn) in LIVE_STRATEGIES.items():
        try:
            result = fn(limit)
        except Exception as exc:  # pragma: no cover - defensive
            result = {"ok": False, "strategy": key, "label": label,
                      "error": str(exc)[:200], "results": [], "count": 0}
        cards.append(result)
    return {
        "ok": True,
        "as_of": date.today().isoformat(),
        "cards": cards,
        "sizing_constants": {
            "vol_target": VOL_TARGET,
            "trading_days": TRADING_DAYS,
            "max_weight": MAX_WEIGHT,
            "adv_participation": ADV_PARTICIPATION,
            "portfolio_capital_inr": PORTFOLIO_CAPITAL,
            "holdings": HOLDINGS,
            "atr_stop_multiple": ATR_STOP_MULTIPLE,
        },
        "validation": {
            "backtest": "NOT RUN",
            "point_in_time": "FAILING — fundamentals are stored by reporting period, not publication date",
            "survivorship": "FAILING — universe is companies listed today",
            "lifecycle": "OPERATIONAL (stage 2 of 7)",
            "alpha_claims_permitted": False,
        },
        "policy": POLICY,
    }
