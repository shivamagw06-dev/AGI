"""Dependency-free Black-Scholes-Merton analytics for the local Options Lab.

This module deliberately accepts normalized, provider-neutral inputs. Live
Upstox and Groww observations will be reconciled before they reach this layer;
the pricing engine never decides which vendor to trust.
"""

from __future__ import annotations

import math
from typing import Any, Callable


_SQRT_2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)
_VOL_LOWER = 0.000001
_VOL_UPPER = 5.0


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / _SQRT_2))


def _normal_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / _SQRT_2PI


def _number(
    payload: dict[str, Any],
    key: str,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    required: bool = True,
) -> float | None:
    raw = payload.get(key, default)
    if raw is None or raw == "":
        if required:
            raise ValueError(f"{key} is required")
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{key} must be a number")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{key} must be no more than {maximum}")
    return value


def _d1_d2(
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> tuple[float, float]:
    root_time = math.sqrt(time_years)
    d1 = (
        math.log(spot / strike)
        + (rate - dividend_yield + 0.5 * volatility * volatility) * time_years
    ) / (volatility * root_time)
    return d1, d1 - volatility * root_time


def _price(
    option_type: str,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> float:
    d1, d2 = _d1_d2(
        spot, strike, time_years, rate, dividend_yield, volatility
    )
    discounted_spot = spot * math.exp(-dividend_yield * time_years)
    discounted_strike = strike * math.exp(-rate * time_years)
    if option_type == "call":
        return discounted_spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
    return discounted_strike * _normal_cdf(-d2) - discounted_spot * _normal_cdf(-d1)


def _bounds(
    option_type: str,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    dividend_yield: float,
) -> tuple[float, float]:
    discounted_spot = spot * math.exp(-dividend_yield * time_years)
    discounted_strike = strike * math.exp(-rate * time_years)
    if option_type == "call":
        return max(0.0, discounted_spot - discounted_strike), discounted_spot
    return max(0.0, discounted_strike - discounted_spot), discounted_strike


def _bracketed_root(
    function: Callable[[float], float],
    low: float,
    high: float,
    *,
    tolerance: float = 1e-9,
    iterations: int = 120,
) -> float:
    """Safeguarded secant/bisection root solver for a monotonic function."""

    f_low = function(low)
    f_high = function(high)
    if f_low == 0.0:
        return low
    if f_high == 0.0:
        return high
    if f_low * f_high > 0.0:
        raise ValueError("root is not bracketed")

    for _ in range(iterations):
        midpoint = 0.5 * (low + high)
        candidate = midpoint
        denominator = f_high - f_low
        if denominator != 0.0:
            secant = high - f_high * (high - low) / denominator
            guard = tolerance * max(1.0, abs(low), abs(high))
            if low + guard < secant < high - guard:
                candidate = secant
        f_candidate = function(candidate)
        if abs(f_candidate) <= tolerance:
            return candidate
        if f_low * f_candidate <= 0.0:
            high, f_high = candidate, f_candidate
        else:
            low, f_low = candidate, f_candidate
        if abs(high - low) <= tolerance * max(1.0, abs(candidate)):
            return 0.5 * (low + high)
    return 0.5 * (low + high)


def _implied_volatility(
    target: float | None,
    option_type: str,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    dividend_yield: float,
) -> float | None:
    if target is None or target <= 0.0:
        return None
    lower_bound, upper_bound = _bounds(
        option_type, spot, strike, time_years, rate, dividend_yield
    )
    epsilon = max(1e-8, spot * 1e-12)
    if target < lower_bound - epsilon or target > upper_bound + epsilon:
        return None

    def objective(volatility: float) -> float:
        return _price(
            option_type,
            spot,
            strike,
            time_years,
            rate,
            dividend_yield,
            volatility,
        ) - target

    try:
        return _bracketed_root(objective, _VOL_LOWER, _VOL_UPPER)
    except ValueError:
        return None


def _greeks(
    option_type: str,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> dict[str, float]:
    d1, d2 = _d1_d2(
        spot, strike, time_years, rate, dividend_yield, volatility
    )
    discount_spot = math.exp(-dividend_yield * time_years)
    discount_strike = math.exp(-rate * time_years)
    root_time = math.sqrt(time_years)
    pdf = _normal_pdf(d1)

    gamma = discount_spot * pdf / (spot * volatility * root_time)
    vega_per_point = spot * discount_spot * pdf * root_time / 100.0
    common_theta = -spot * discount_spot * pdf * volatility / (2.0 * root_time)

    if option_type == "call":
        delta = discount_spot * _normal_cdf(d1)
        theta_annual = (
            common_theta
            - rate * strike * discount_strike * _normal_cdf(d2)
            + dividend_yield * spot * discount_spot * _normal_cdf(d1)
        )
        rho_per_point = strike * time_years * discount_strike * _normal_cdf(d2) / 100.0
    else:
        delta = discount_spot * (_normal_cdf(d1) - 1.0)
        theta_annual = (
            common_theta
            + rate * strike * discount_strike * _normal_cdf(-d2)
            - dividend_yield * spot * discount_spot * _normal_cdf(-d1)
        )
        rho_per_point = -strike * time_years * discount_strike * _normal_cdf(-d2) / 100.0

    return {
        "delta": delta,
        "gamma": gamma,
        "theta_per_day": theta_annual / 365.0,
        "vega_per_vol_point": vega_per_point,
        "rho_per_rate_point": rho_per_point,
    }


def _round(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(value, digits)


def price_option_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Price one European option snapshot and return client-safe analytics."""

    if not isinstance(payload, dict):
        raise ValueError("request body must be an object")
    option_type = str(payload.get("option_type") or "call").strip().lower()
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be call or put")

    spot = _number(payload, "spot", minimum=0.000001, maximum=100_000_000.0)
    strike = _number(payload, "strike", minimum=0.000001, maximum=100_000_000.0)
    days = _number(payload, "days_to_expiry", minimum=0.000001, maximum=3650.0)
    rate_pct = _number(payload, "risk_free_rate_pct", default=5.5, minimum=-10.0, maximum=100.0)
    dividend_pct = _number(payload, "dividend_yield_pct", default=0.0, minimum=0.0, maximum=100.0)
    model_vol_pct = _number(payload, "model_volatility_pct", default=18.0, minimum=0.01, maximum=500.0)
    bid = _number(payload, "bid", required=False, minimum=0.0, maximum=100_000_000.0)
    ask = _number(payload, "ask", required=False, minimum=0.0, maximum=100_000_000.0)
    last_price = _number(payload, "last_price", required=False, minimum=0.0, maximum=100_000_000.0)
    multiplier = _number(payload, "contract_multiplier", default=1.0, minimum=0.000001, maximum=10_000_000.0)

    if (bid is None) != (ask is None):
        raise ValueError("bid and ask must be supplied together")
    if bid is not None and ask is not None and ask < bid:
        raise ValueError("ask must be greater than or equal to bid")

    time_years = days / 365.0
    rate = rate_pct / 100.0
    dividend_yield = dividend_pct / 100.0
    model_volatility = model_vol_pct / 100.0
    market_mid = (bid + ask) / 2.0 if bid is not None and ask is not None else last_price

    fair_value = _price(
        option_type, spot, strike, time_years, rate, dividend_yield, model_volatility
    )
    intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
    lower_bound, upper_bound = _bounds(
        option_type, spot, strike, time_years, rate, dividend_yield
    )

    iv_bid = _implied_volatility(
        bid, option_type, spot, strike, time_years, rate, dividend_yield
    )
    iv_mid = _implied_volatility(
        market_mid, option_type, spot, strike, time_years, rate, dividend_yield
    )
    iv_ask = _implied_volatility(
        ask, option_type, spot, strike, time_years, rate, dividend_yield
    )
    greeks_volatility = iv_mid or model_volatility
    greeks = _greeks(
        option_type,
        spot,
        strike,
        time_years,
        rate,
        dividend_yield,
        greeks_volatility,
    )

    spread = ask - bid if bid is not None and ask is not None else None
    spread_pct = (
        spread / market_mid * 100.0
        if spread is not None and market_mid is not None and market_mid > 0.0
        else None
    )
    difference = market_mid - fair_value if market_mid is not None else None
    difference_pct = (
        difference / fair_value * 100.0
        if difference is not None and fair_value > 0.0
        else None
    )
    tolerance = max(fair_value * 0.02, 0.05, (spread or 0.0) / 2.0)
    if market_mid is None:
        assessment = "model_only"
    elif difference is not None and difference > tolerance:
        assessment = "expensive"
    elif difference is not None and difference < -tolerance:
        assessment = "cheap"
    else:
        assessment = "fair"

    warnings: list[str] = []
    if market_mid is None:
        warnings.append("No market quote supplied; implied volatility and relative valuation are unavailable.")
    if spread_pct is not None and spread_pct > 8.0:
        warnings.append("Bid-ask spread is wider than 8%; valuation confidence is reduced.")
    if market_mid is not None and not (lower_bound <= market_mid <= upper_bound):
        warnings.append("Market midpoint violates model no-arbitrage bounds; midpoint IV is unavailable.")
    if market_mid is not None and iv_mid is None:
        warnings.append("A stable midpoint implied volatility could not be solved from this quote.")

    expected_move = spot * greeks_volatility * math.sqrt(time_years)
    reference_price = market_mid if market_mid is not None else fair_value
    scenario_specs = [
        ("Down shock", -2.0, 3.0),
        ("Down move", -1.0, 0.0),
        ("Volatility falls", 0.0, -3.0),
        ("Unchanged", 0.0, 0.0),
        ("Volatility rises", 0.0, 3.0),
        ("Up move", 1.0, 0.0),
        ("Up shock", 2.0, 3.0),
    ]
    scenarios: list[dict[str, Any]] = []
    for label, spot_change_pct, vol_change_points in scenario_specs:
        scenario_spot = spot * (1.0 + spot_change_pct / 100.0)
        scenario_vol = max(_VOL_LOWER, greeks_volatility + vol_change_points / 100.0)
        scenario_price = _price(
            option_type,
            scenario_spot,
            strike,
            time_years,
            rate,
            dividend_yield,
            scenario_vol,
        )
        scenarios.append(
            {
                "label": label,
                "spot_change_pct": spot_change_pct,
                "volatility_change_points": vol_change_points,
                "option_value": _round(scenario_price, 4),
                "pnl_per_contract": _round((scenario_price - reference_price) * multiplier, 2),
            }
        )

    if market_mid is None:
        quality_status = "model_only"
    elif iv_mid is None:
        quality_status = "invalid_market_quote"
    elif warnings:
        quality_status = "warning"
    else:
        quality_status = "usable"

    return {
        "model": {
            "name": "Black-Scholes-Merton",
            "version": "agi-bsm-v1-local",
            "local_only": True,
            "exercise_style": "european",
        },
        "inputs": {
            "option_type": option_type,
            "spot": spot,
            "strike": strike,
            "days_to_expiry": days,
            "time_years": _round(time_years, 9),
            "risk_free_rate_pct": rate_pct,
            "dividend_yield_pct": dividend_pct,
            "model_volatility_pct": model_vol_pct,
            "contract_multiplier": multiplier,
        },
        "market": {
            "bid": bid,
            "ask": ask,
            "last_price": last_price,
            "mid": _round(market_mid, 4),
            "spread": _round(spread, 4),
            "spread_pct": _round(spread_pct, 3),
        },
        "valuation": {
            "model_value": _round(fair_value, 4),
            "intrinsic_value": _round(intrinsic, 4),
            "extrinsic_value": _round(max(fair_value - intrinsic, 0.0), 4),
            "market_minus_model": _round(difference, 4),
            "market_minus_model_pct": _round(difference_pct, 3),
            "assessment": assessment,
            "no_arbitrage_lower": _round(lower_bound, 4),
            "no_arbitrage_upper": _round(upper_bound, 4),
            "model_contract_value": _round(fair_value * multiplier, 2),
        },
        "implied_volatility": {
            "bid_pct": _round(iv_bid * 100.0 if iv_bid is not None else None, 4),
            "mid_pct": _round(iv_mid * 100.0 if iv_mid is not None else None, 4),
            "ask_pct": _round(iv_ask * 100.0 if iv_ask is not None else None, 4),
            "solver_bounds_pct": [_VOL_LOWER * 100.0, _VOL_UPPER * 100.0],
        },
        "greeks": {
            **{key: _round(value, 8) for key, value in greeks.items()},
            "basis_volatility_pct": _round(greeks_volatility * 100.0, 4),
        },
        "risk": {
            "one_sigma_expected_move": _round(expected_move, 2),
            "one_sigma_lower": _round(spot - expected_move, 2),
            "one_sigma_upper": _round(spot + expected_move, 2),
        },
        "scenarios": scenarios,
        "quality": {
            "status": quality_status,
            "warnings": warnings,
            "input_provenance": "manual_local_snapshot",
        },
        "disclaimer": (
            "Research analytics only. Model outputs are estimates, not forecasts, "
            "recommendations, or guarantees of executable prices."
        ),
    }
