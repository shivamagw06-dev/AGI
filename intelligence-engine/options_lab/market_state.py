"""What the options market looked like on one day, and only on that day.

Every column here must have been knowable at that close. Realised volatility
looks backwards, positioning is the book as it stood, implied levels come from
that day's fitted surfaces.

That rule is the whole point of the module rather than a detail of it. The
variance risk premium -- implied against the volatility that actually followed
-- is the more useful number, and it is deliberately not here. A state row
carrying it would let a study condition on what happened next and report an
edge nobody could have traded. It belongs with the outcomes.

Positioning uses near-dated expiries only. A December strike carries open
interest that says nothing about this week, and pooling it flatters every
concentration measure.
"""

from __future__ import annotations

import math
import statistics
from datetime import date
from typing import Any, Optional

from . import volatility

STATE_VERSION = "state-1"

# Positioning windows. Beyond about two months, open interest is hedging and
# structural rather than a view on the next few days.
NEAR_DTE = 45
# Enough of a chain to say anything about concentration or max pain.
MIN_CONTRACTS = 40
MIN_CONTRACTS_HIGH = 200
# Realised volatility needs its window filled. A twenty-day number computed
# from three returns is a three-day number wearing a twenty-day label, and it
# reads about half the true level: the first week of the warehouse produced
# 4.65 and 4.95 where every later day sat between 8.9 and 13.5, which inflated
# the implied-minus-realised spread from +0.22 to +1.20 across the series.
#
# So a window must be full, not merely non-empty. Short of that the column is
# null, which is the honest answer for a statistic that cannot yet be measured.
RV_WINDOWS = (5, 20)
# A little tolerance for the odd missing close, but not enough to change what
# the number means.
RV_MIN_FILL = 0.9
TRADING_DAYS = 252


def _annualised(returns: list[float], window: int) -> Optional[float]:
    """Annualised volatility, or nothing if the window is not filled."""
    if len(returns) < max(3, int(window * RV_MIN_FILL)):
        return None
    return statistics.pstdev(returns) * math.sqrt(TRADING_DAYS) * 100.0


def realised_vols(closes: list[tuple[str, float]]) -> dict[str, Optional[float]]:
    """Trailing realised volatility from a spot series ending on the last date.

    Expects closes oldest first, the final entry being the day being described.
    """
    series = [c for _, c in closes if c and c > 0]
    rets = [math.log(series[i] / series[i - 1]) for i in range(1, len(series))]
    out: dict[str, Optional[float]] = {}
    for window in RV_WINDOWS:
        out[f"realised_vol_{window}d"] = (
            _annualised(rets[-window:], window) if rets else None)
    out["return_1d_pct"] = round(rets[-1] * 100.0, 4) if rets else None
    return out


def max_pain(contracts: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """The strike where writers owe least, and how the book sits around it.

    Total intrinsic owed if the underlying settled at each listed strike. This
    is an observation about positioning, not a forecast: whether price is drawn
    toward it is exactly the kind of market lore the warehouse exists to test
    rather than assume.
    """
    calls: dict[float, int] = {}
    puts: dict[float, int] = {}
    for row in contracts:
        strike = float(row.get("strike") or 0)
        oi = int(row.get("open_interest") or 0)
        if strike <= 0 or oi <= 0:
            continue
        side = calls if row.get("option_type") == "CE" else puts
        side[strike] = side.get(strike, 0) + oi

    strikes = sorted(set(calls) | set(puts))
    if len(strikes) < 3:
        return None

    best_strike, best_pain = None, None
    for settle in strikes:
        pain = sum(oi * max(0.0, settle - k) for k, oi in calls.items())
        pain += sum(oi * max(0.0, k - settle) for k, oi in puts.items())
        if best_pain is None or pain < best_pain:
            best_strike, best_pain = settle, pain

    call_total = sum(calls.values())
    put_total = sum(puts.values())
    peak_call = max(calls, key=calls.get) if calls else None
    peak_put = max(puts, key=puts.get) if puts else None
    return {
        "max_pain": best_strike,
        "total_call_oi": call_total,
        "total_put_oi": put_total,
        "peak_call_oi_strike": peak_call,
        "peak_put_oi_strike": peak_put,
        "call_oi_concentration": (round(calls[peak_call] / call_total, 4)
                                  if peak_call and call_total else None),
        "put_oi_concentration": (round(puts[peak_put] / put_total, 4)
                                 if peak_put and put_total else None),
    }


def _ratio(puts: float, calls: float) -> Optional[float]:
    """Put over call, guarding the case that makes it meaningless.

    A put-call ratio with no calls is not infinity, it is a chain too thin to
    describe. Returning a number there would put an outlier into every
    percentile that follows.
    """
    if not calls:
        return None
    return round(puts / calls, 4)


# An expiry carrying a small share of the day's fitted points is thinly traded
# whatever its rmse says, and NIFTY lists monthlies that barely trade beside
# the weeklies.
THIN_POINT_SHARE = 0.5


def _interp(a: dict[str, Any], b: dict[str, Any], field: str,
            target: int) -> Optional[float]:
    x0, x1 = int(a["dte_days"]), int(b["dte_days"])
    y0, y1 = a.get(field), b.get(field)
    if y0 is None or y1 is None:
        return None
    if x1 == x0:
        return float(y0)
    w = (target - x0) / (x1 - x0)
    return round(float(y0) + w * (float(y1) - float(y0)), 4)


def _thirty_day_point(surfaces: list[dict[str, Any]],
                      target: int = 30) -> Optional[dict[str, Any]]:
    """A thirty-day surface interpolated between the expiries either side.

    Taking the single nearest expiry looks equivalent and is not. On
    21 Aug 2026 the nearest to thirty days was a monthly with nineteen fitted
    points and a risk reversal of +1.78, where every neighbouring expiry sat
    between -0.6 and -2.2. Read on proximity alone, the skew for that day
    changes sign -- and skew sign is exactly what a skew study keys on.

    So thin expiries are dropped first, then the value is interpolated across
    the two survivors that bracket the target. A term structure is a curve; one
    point on it is a sample, and a sparse sample at that.
    """
    if not surfaces:
        return None
    points = [int(s.get("fit_points") or 0) for s in surfaces]
    floor = statistics.median(points) * THIN_POINT_SHARE if points else 0
    solid = [s for s in surfaces if int(s.get("fit_points") or 0) >= floor] or surfaces
    solid = sorted(solid, key=lambda s: int(s["dte_days"]))

    below = [s for s in solid if int(s["dte_days"]) <= target]
    above = [s for s in solid if int(s["dte_days"]) >= target]
    if below and above:
        a, b = below[-1], above[0]
        if a is b:
            return dict(a)
        return {
            "dte_days": target,
            "atm_iv": _interp(a, b, "atm_iv", target),
            "risk_reversal": _interp(a, b, "risk_reversal", target),
            "butterfly": _interp(a, b, "butterfly", target),
            "surface_quality": ("high" if a.get("surface_quality") == "high"
                                and b.get("surface_quality") == "high" else "medium"),
        }
    # Only one side exists: use the closest rather than extrapolate a curve
    # beyond the expiries that were actually listed.
    return dict(min(solid, key=lambda s: abs(int(s["dte_days"]) - target)))


def build(observations: list[dict[str, Any]],
          surfaces: list[dict[str, Any]],
          spot_history: list[tuple[str, float]]) -> Optional[dict[str, Any]]:
    """One state row from one day's observations, surfaces and prior closes."""
    if not observations:
        return None
    day = str(observations[0]["observation_date"])
    underlying = str(observations[0]["underlying_symbol"])

    # Near-dated only, with no fallback to the whole chain. Widening the window
    # when the near expiries are thin does not rescue the number, it changes
    # what the number means: one far-dated strike carrying nine million lots
    # becomes "the" peak open interest, and every concentration measure for the
    # day describes hedging nobody put on this week. Too few contracts is
    # reported as low quality instead.
    near = [o for o in observations if int(o.get("dte_days") or 999) <= NEAR_DTE]

    calls = [o for o in near if o.get("option_type") == "CE"]
    puts = [o for o in near if o.get("option_type") == "PE"]

    def total(rows, field):
        return sum(abs(int(r.get(field) or 0)) for r in rows)

    positioning = max_pain(near) or {}
    spot = next((float(o["underlying_spot"]) for o in observations
                 if o.get("underlying_spot")), None)

    # Surfaces: the front month, and a thirty-day point read off the term
    # structure rather than taken from whichever expiry happens to sit nearest.
    usable = sorted((s for s in surfaces if s.get("atm_iv")),
                    key=lambda s: int(s.get("dte_days") or 0))
    front = usable[0] if usable else None
    thirty = _thirty_day_point(usable)

    # How much the expiries agree about skew. Two attempts to suppress one
    # disagreeing expiry were two attempts too many: negative skew is the usual
    # equity direction, not a law, and filtering until the data agrees with that
    # prior is how a method gets fitted to its expected answer. So the
    # disagreement is measured and stored, and a study can require agreement or
    # study the days that lack it.
    rrs = [float(x["risk_reversal"]) for x in usable
           if x.get("risk_reversal") is not None]
    if rrs and thirty and thirty.get("risk_reversal") is not None:
        sign = 1 if float(thirty["risk_reversal"]) >= 0 else -1
        agree = sum(1 for r in rrs if (1 if r >= 0 else -1) == sign)
        skew_agreement = round(agree / len(rrs), 4)
    else:
        skew_agreement = None

    vols = realised_vols(spot_history)
    atm_30 = float(thirty["atm_iv"]) if thirty else None
    rv20 = vols.get("realised_vol_20d")

    contracts_used = len(near)
    if contracts_used >= MIN_CONTRACTS_HIGH and front and thirty and rv20:
        quality = "high"
    elif contracts_used >= MIN_CONTRACTS and (front or thirty):
        quality = "medium"
    else:
        # Either the near-dated chain is too thin to describe positioning, or
        # there is no usable surface. The row still exists -- what it does hold
        # is real -- but nothing should key on it without looking here first.
        quality = "low"

    return {
        "observation_date": day,
        "underlying_symbol": underlying,
        "spot": round(spot, 4) if spot else None,
        "return_1d_pct": vols.get("return_1d_pct"),
        "realised_vol_5d": (round(vols["realised_vol_5d"], 4)
                            if vols.get("realised_vol_5d") else None),
        "realised_vol_20d": round(rv20, 4) if rv20 else None,
        "atm_iv_front": float(front["atm_iv"]) if front else None,
        "atm_iv_30d": atm_30,
        "term_slope": (round(atm_30 - float(front["atm_iv"]), 4)
                       if atm_30 and front else None),
        "risk_reversal_30d": (float(thirty["risk_reversal"])
                              if thirty and thirty.get("risk_reversal") is not None
                              else None),
        "skew_agreement": skew_agreement,
        "butterfly_30d": (float(thirty["butterfly"])
                          if thirty and thirty.get("butterfly") is not None else None),
        "iv_minus_trailing_rv": (round(atm_30 - rv20, 4)
                                 if atm_30 and rv20 else None),
        "oi_pcr": _ratio(total(puts, "open_interest"), total(calls, "open_interest")),
        "volume_pcr": _ratio(total(puts, "volume"), total(calls, "volume")),
        "change_oi_pcr": _ratio(total(puts, "change_open_interest"),
                                total(calls, "change_open_interest")),
        "total_call_oi": positioning.get("total_call_oi"),
        "total_put_oi": positioning.get("total_put_oi"),
        "max_pain": positioning.get("max_pain"),
        "spot_to_max_pain_pct": (round((spot / positioning["max_pain"] - 1) * 100, 4)
                                 if spot and positioning.get("max_pain") else None),
        "peak_call_oi_strike": positioning.get("peak_call_oi_strike"),
        "peak_put_oi_strike": positioning.get("peak_put_oi_strike"),
        "call_oi_concentration": positioning.get("call_oi_concentration"),
        "put_oi_concentration": positioning.get("put_oi_concentration"),
        "expiries_used": len({str(o["expiry"]) for o in near}),
        "contracts_used": min(contracts_used, 32767),
        "state_quality": quality,
        "state_version": STATE_VERSION,
    }


def build_day(day, *, underlying: str = "NIFTY",
              dry_run: bool = True) -> dict[str, Any]:
    """Build and store one day's market state from what is already warehoused."""
    from . import canonical_store

    try:
        # Every contract, not only the ones whose volatility solved. Open
        # interest is real whether or not a smile could be fitted to it.
        observations = canonical_store.observations_for_day(
            day, underlying, usable_iv_only=False)
        surfaces = canonical_store.surfaces_for_day(day, underlying)
        history = canonical_store.spot_history(day, underlying)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "read", "error": str(exc)[:250]}
    if not observations:
        return {"ok": False, "stage": "read",
                "error": "no observations stored for that day"}

    state = build(observations, surfaces, history)
    if not state:
        return {"ok": False, "stage": "build", "observations": len(observations),
                "error": "could not describe that day"}
    try:
        written = canonical_store.upsert_state(state, dry_run=dry_run)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "write", "error": str(exc)[:250]}
    return {"ok": True, "stage": "complete", "observations": len(observations),
            "surfaces": len(surfaces), "history_days": len(history),
            "state_quality": state["state_quality"],
            "skew_agreement": state.get("skew_agreement"), "write": written}
