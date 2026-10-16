"""P0 pair statistics — OLS hedge, spread z-score, EG cointegration, half-life."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OLSResult:
    alpha: float
    beta: float
    residuals: tuple[float, ...]
    r_squared: float


@dataclass(frozen=True)
class CointegrationResult:
    cointegrated: bool
    adf_stat: float
    p_value_proxy: float
    critical_value: float


@dataclass(frozen=True)
class HalfLifeResult:
    half_life: float | None
    phi: float
    valid: bool


def ols_hedge(y: list[float], x: list[float]) -> OLSResult:
    """OLS: y = alpha + beta * x. Deterministic pure-Python."""
    n = min(len(y), len(x))
    if n < 3:
        return OLSResult(alpha=0.0, beta=1.0, residuals=tuple(), r_squared=0.0)
    ys = y[-n:]
    xs = x[-n:]
    mx = sum(xs) / n
    my = sum(ys) / n
    var_x = sum((v - mx) ** 2 for v in xs)
    if var_x < 1e-18:
        beta = 0.0
        alpha = my
    else:
        cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        beta = cov / var_x
        alpha = my - beta * mx
    resid = [b - (alpha + beta * a) for a, b in zip(xs, ys)]
    ss_tot = sum((b - my) ** 2 for b in ys)
    ss_res = sum(r * r for r in resid)
    r2 = 0.0 if ss_tot < 1e-18 else max(0.0, 1.0 - ss_res / ss_tot)
    return OLSResult(
        alpha=round(alpha, 10),
        beta=round(beta, 10),
        residuals=tuple(round(r, 10) for r in resid),
        r_squared=round(r2, 8),
    )


def spread_series(y: list[float], x: list[float], alpha: float, beta: float) -> list[float]:
    n = min(len(y), len(x))
    return [y[-n + i] - alpha - beta * x[-n + i] for i in range(n)]


def zscore(series: list[float]) -> tuple[float, float, float]:
    """Return (last_z, mean, std)."""
    if len(series) < 2:
        return 0.0, 0.0, 0.0
    mu = sum(series) / len(series)
    var = sum((v - mu) ** 2 for v in series) / (len(series) - 1)
    sigma = math.sqrt(max(var, 0.0))
    if sigma < 1e-12:
        return 0.0, mu, 0.0
    return round((series[-1] - mu) / sigma, 8), round(mu, 10), round(sigma, 10)


def engle_granger(residuals: list[float] | tuple[float, ...]) -> CointegrationResult:
    """Engle-Granger residual ADF (no-constant) statistic + deterministic critical proxy.

    Uses Δe_t = γ e_{t-1} + ε_t. Reject unit root (cointegrated) when adf_stat < critical.
    Near-zero residual variance (perfect OLS fit) is treated as cointegrated.
    """
    e = list(residuals)
    n = len(e)
    crit = -2.86
    if n < 8:
        return CointegrationResult(
            cointegrated=False,
            adf_stat=0.0,
            p_value_proxy=1.0,
            critical_value=crit,
        )
    # Perfect / near-perfect hedge residual → cointegrated by construction
    mu = sum(e) / n
    var_e = sum((v - mu) ** 2 for v in e) / max(1, n - 1)
    if var_e < 1e-12:
        return CointegrationResult(
            cointegrated=True,
            adf_stat=-99.0,
            p_value_proxy=0.001,
            critical_value=crit,
        )
    # lag-1 levels and diffs
    y = [e[i] - e[i - 1] for i in range(1, n)]
    x = e[:-1]
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    var_x = sum((v - mx) ** 2 for v in x)
    if var_x < 1e-18:
        return CointegrationResult(
            cointegrated=True,
            adf_stat=-99.0,
            p_value_proxy=0.001,
            critical_value=crit,
        )
    gamma = sum((a - mx) * (b - my) for a, b in zip(x, y)) / var_x
    fitted = [gamma * a for a in x]
    resid = [b - f for b, f in zip(y, fitted)]
    s2 = sum(r * r for r in resid) / max(1, len(resid) - 1)
    se = math.sqrt(s2 / var_x) if var_x > 1e-18 else 1.0
    adf = gamma / se if se > 1e-18 else 0.0
    # Map distance below critical to a p-value proxy in (0,1]
    if adf >= 0:
        p = 1.0
    else:
        # more negative ⇒ smaller p
        p = max(0.001, min(1.0, math.exp(adf)))  # e^{-3}≈0.05 scale-ish
    cointegrated = adf < crit
    return CointegrationResult(
        cointegrated=cointegrated,
        adf_stat=round(adf, 8),
        p_value_proxy=round(p, 8),
        critical_value=crit,
    )


def half_life(spread: list[float]) -> HalfLifeResult:
    """AR(1) half-life: S_t = phi * S_{t-1} + eps; hl = -ln(2)/ln(phi)."""
    if len(spread) < 8:
        return HalfLifeResult(half_life=None, phi=0.0, valid=False)
    y = spread[1:]
    x = spread[:-1]
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    var_x = sum((v - mx) ** 2 for v in x)
    if var_x < 1e-18:
        return HalfLifeResult(half_life=None, phi=0.0, valid=False)
    phi = sum((a - mx) * (b - my) for a, b in zip(x, y)) / var_x
    if phi <= 0.0 or phi >= 1.0:
        return HalfLifeResult(half_life=None, phi=round(phi, 8), valid=False)
    hl = -math.log(2.0) / math.log(phi)
    if not math.isfinite(hl) or hl <= 0 or hl > 500:
        return HalfLifeResult(half_life=None, phi=round(phi, 8), valid=False)
    return HalfLifeResult(half_life=round(hl, 6), phi=round(phi, 8), valid=True)
