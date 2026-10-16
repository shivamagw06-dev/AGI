"""Fitting a volatility surface to the strikes that actually traded.

Nothing here is quoted by the exchange. ATM volatility, skew and curvature are
reconstructed from observed points, so every row carries what it was built from
and how well the fit described it. A study can then require agreement rather
than trust a number because it exists -- the same discipline the forward and
the implied volatility already carry.

Two choices worth stating.

The smile is fitted in log-moneyness, not strike. A 200-point strike step means
something different on a 24,000 index than on a 500 stock, and the same expiry
at different spot levels is not comparable in strike space. Log-moneyness makes
a June surface and an August surface the same shape measured the same way.

A quadratic, not a spline. Three parameters over roughly forty traded strikes
cannot chase noise, and level, slope and curvature are exactly the three things
the downstream studies ask for. A spline would fit the wings better and would
also happily fit one stale quote.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Optional

from .engine import _greeks

SURFACE_VERSION = "quadratic-logk-1"

# The band has to scale with how far the market can actually travel before
# expiry. A fixed log-moneyness band is 31 standard deviations wide on a
# four-day expiry and barely two on a one-year one: the first fits contracts
# trading at thirty paise with 253% implied volatility, the second throws away
# the whole smile. So points are kept by standardised moneyness, k / (sigma
# * sqrt(T)), which means the same thing at every maturity.
FIT_BAND_SD = 3.0
# Enough near-the-money points to estimate the sigma that defines the band.
SEED_POINTS = 6
# A real smile does not have wings thirty times its own level. Inside the band
# there are still contracts trading at thirty paise whose solved volatility
# comes back at 255% against an at-the-money 7.8%, and three of those are
# enough to drag a quadratic to a negative at-the-money volatility. The bound
# is relative to the seed because 255% is absurd on this chain and unremarkable
# on a single stock in a crisis.
IV_MULTIPLE_MAX = 3.0
IV_MULTIPLE_MIN = 0.25
# The relative bound is measured against a median of near-money points, so it
# inherits their judgement. If enough of those are themselves nonsense the
# median lands on nonsense and the whole surface agrees with itself. An index
# does not trade at 300% at the money, and nothing liquid enough to fit does.
ATM_ABS_MIN_PCT = 1.0
ATM_ABS_MAX_PCT = 200.0
# One robust pass: fit, drop what the fit cannot explain, fit again. A single
# stale wing quote survives every band and only shows itself as a residual.
OUTLIER_SD = 3.0
MIN_POINTS = 5
MIN_POINTS_HIGH = 12
MAX_RMSE_HIGH = 1.5      # volatility points
MAX_RMSE_ANY = 6.0

WING_DELTA = 0.25


def _quadratic_fit(xs: list[float], ys: list[float]) -> Optional[tuple[float, float, float]]:
    """Least squares y = a + b*x + c*x^2, solved directly.

    Three normal equations by hand rather than a matrix library: the engine
    does not carry numpy, and a 3x3 solve is not worth an import.
    """
    n = len(xs)
    if n < 3:
        return None
    s = [sum(x ** p for x in xs) for p in range(5)]
    t = [sum(y * x ** p for x, y in zip(xs, ys)) for p in range(3)]
    # [ n    s1   s2 ] [a]   [t0]
    # [ s1   s2   s3 ] [b] = [t1]
    # [ s2   s3   s4 ] [c]   [t2]
    m = [[s[0], s[1], s[2], t[0]],
         [s[1], s[2], s[3], t[1]],
         [s[2], s[3], s[4], t[2]]]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(3):
            if r == col:
                continue
            factor = m[r][col] / m[col][col]
            for k in range(col, 4):
                m[r][k] -= factor * m[col][k]
    return tuple(m[i][3] / m[i][i] for i in range(3))


def _interpolate_at(points: list[tuple[float, float]], target: float) -> Optional[float]:
    """Linear interpolation of y at x = target, from points sorted by x.

    Refuses to extrapolate. A 25-delta volatility invented beyond the observed
    deltas is a statement about strikes nobody traded.
    """
    if len(points) < 2:
        return None
    pts = sorted(points)
    if target < pts[0][0] or target > pts[-1][0]:
        return None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= target <= x1:
            if x1 == x0:
                return y0
            weight = (target - x0) / (x1 - x0)
            return y0 + weight * (y1 - y0)
    return None


def fit_expiry(rows: list[dict[str, Any]], *,
               rate_pct: float = 5.25) -> Optional[dict[str, Any]]:
    """One expiry's surface from its traded contracts.

    Expects canonical rows: strike, option_type, implied_volatility, iv_quality,
    forward, dte_days. Rows without a usable volatility are ignored here rather
    than dropped from the warehouse -- they still matter to an open-interest
    study, they just cannot describe a smile.
    """
    usable = [r for r in rows
              if r.get("iv_quality") == "ok" and r.get("implied_volatility")
              and r.get("forward") and r.get("strike")]
    if len(usable) < MIN_POINTS:
        return None

    first = usable[0]
    forward = float(first["forward"])
    dte = int(first["dte_days"])
    time_years = max(dte, 1) / 365.0
    rate = rate_pct / 100.0

    observed: list[tuple[float, float, str, float]] = []   # k, iv, type, strike
    for row in usable:
        strike = float(row["strike"])
        iv_pct = float(row["implied_volatility"])
        if strike <= 0 or iv_pct <= 0:
            continue
        observed.append((math.log(strike / forward), iv_pct, row["option_type"], strike))
    if len(observed) < MIN_POINTS:
        return None

    # Seed sigma from the points nearest the money, where both sides are liquid
    # and implied volatility is least sensitive to a tick.
    seed = sorted(observed, key=lambda o: abs(o[0]))[:SEED_POINTS]
    sigma = statistics.median(iv for _, iv, _, _ in seed) / 100.0
    if sigma <= 0:
        return None
    unit = sigma * math.sqrt(time_years)
    if unit <= 0:
        return None

    fit_points: list[tuple[float, float]] = []
    call_wing: list[tuple[float, float]] = []
    put_wing: list[tuple[float, float]] = []

    for k, iv_pct, kind, strike in observed:
        # Out of the money only. An in-the-money option is mostly intrinsic
        # value, so its price says little about volatility and its implied
        # volatility is dominated by the bid-ask on a large premium.
        if kind == "CE" and k < -unit:
            continue
        if kind == "PE" and k > unit:
            continue
        if abs(k) > FIT_BAND_SD * unit:
            continue
        if not (IV_MULTIPLE_MIN * sigma * 100 <= iv_pct <= IV_MULTIPLE_MAX * sigma * 100):
            continue
        fit_points.append((k, iv_pct))
        greeks = _greeks("call" if kind == "CE" else "put",
                         forward, strike, time_years, rate, rate, iv_pct / 100.0)
        delta = (greeks or {}).get("delta")
        if delta is None:
            continue
        (call_wing if kind == "CE" else put_wing).append((delta, iv_pct))

    if len(fit_points) < MIN_POINTS:
        return None

    def _fit(points):
        coeffs = _quadratic_fit([k for k, _ in points], [v for _, v in points])
        if not coeffs:
            return None, None, None
        a, b, c = coeffs
        res = [v - (a + b * k + c * k * k) for k, v in points]
        return coeffs, res, math.sqrt(sum(r * r for r in res) / len(res))

    coeffs, residuals, rmse = _fit(fit_points)
    if not coeffs:
        return None
    if rmse > 0:
        kept = [pt for pt, r in zip(fit_points, residuals)
                if abs(r) <= OUTLIER_SD * rmse]
        if MIN_POINTS <= len(kept) < len(fit_points):
            refit, refit_res, refit_rmse = _fit(kept)
            if refit:
                fit_points, coeffs, residuals, rmse = kept, refit, refit_res, refit_rmse
    a, b, c = coeffs

    atm_iv = a                      # the fit evaluated at k = 0
    atm_slope = b                   # d(iv)/dk at the money
    call_25 = _interpolate_at(call_wing, WING_DELTA)
    put_25 = _interpolate_at(put_wing, -WING_DELTA)

    risk_reversal = (call_25 - put_25) if (call_25 and put_25) else None
    butterfly = (((call_25 + put_25) / 2.0) - atm_iv
                 if (call_25 and put_25 and atm_iv) else None)

    # A fitted at-the-money volatility that is negative, or nowhere near the
    # level the traded near-money strikes actually showed, means the curve went
    # somewhere the data did not. Returning it graded "low" would still put it
    # in a percentile study; refusing is the honest answer.
    if not (IV_MULTIPLE_MIN * sigma * 100 <= atm_iv <= IV_MULTIPLE_MAX * sigma * 100):
        return None
    if not (ATM_ABS_MIN_PCT <= atm_iv <= ATM_ABS_MAX_PCT):
        return None

    if len(fit_points) >= MIN_POINTS_HIGH and rmse <= MAX_RMSE_HIGH:
        quality = "high"
    elif rmse <= MAX_RMSE_ANY:
        quality = "medium"
    else:
        quality = "low"

    return {
        "observation_date": first["observation_date"],
        "underlying_symbol": first["underlying_symbol"],
        "expiry": first["expiry"],
        "dte_days": dte,
        "forward": round(forward, 4),
        "forward_quality": first.get("forward_quality"),
        "atm_iv": round(atm_iv, 4),
        "call_25d_iv": round(call_25, 4) if call_25 else None,
        "put_25d_iv": round(put_25, 4) if put_25 else None,
        "risk_reversal": round(risk_reversal, 4) if risk_reversal is not None else None,
        "butterfly": round(butterfly, 4) if butterfly is not None else None,
        "atm_slope": round(atm_slope, 4),
        "fit_points": len(fit_points),
        "fit_rmse": round(rmse, 4),
        "surface_quality": quality,
        "surface_version": SURFACE_VERSION,
    }


def fit_day(rows: list[dict[str, Any]], *,
            rate_pct: float = 5.25) -> list[dict[str, Any]]:
    """Every expiry's surface for one trading day."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("observation_date")), str(row.get("underlying_symbol")),
               str(row.get("expiry")))
        grouped.setdefault(key, []).append(row)
    out = []
    for _, chain in sorted(grouped.items()):
        fitted = fit_expiry(chain, rate_pct=rate_pct)
        if fitted:
            out.append(fitted)
    return out


def build_day(day, *, underlying: Optional[str] = "NIFTY",
              dry_run: bool = True) -> dict[str, Any]:
    """Fit and store every surface for one trading day.

    Reads the canonical observations back rather than re-deriving them from
    NSE. The surface must describe the same numbers a study will later join
    to, and re-deriving invites the two to drift apart the first time the
    pipeline changes.
    """
    from . import canonical_store

    try:
        rows = canonical_store.observations_for_day(day, underlying)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "read", "error": str(exc)[:250]}
    if not rows:
        return {"ok": False, "stage": "read", "observations": 0,
                "error": "no usable observations stored for that day"}

    fitted = fit_day(rows)
    if not fitted:
        return {"ok": False, "stage": "fit", "observations": len(rows),
                "error": "no expiry produced a usable surface"}

    quality: dict[str, int] = {}
    for s in fitted:
        quality[s["surface_quality"]] = quality.get(s["surface_quality"], 0) + 1
    try:
        written = canonical_store.upsert_surfaces(fitted, dry_run=dry_run)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "write", "fitted": len(fitted),
                "error": str(exc)[:250]}
    return {"ok": True, "stage": "complete", "observations": len(rows),
            "expiries_fitted": len(fitted), "surface_quality": quality,
            "write": written}
