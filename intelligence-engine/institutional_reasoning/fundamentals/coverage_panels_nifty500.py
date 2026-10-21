"""Track 1 — Nifty 500 coverage panels (parametric institutional fixtures).

Registers Infosys-class primitive panels for Tier-2 names not already
covered by Target-20 / Nifty 50 / Nifty 100 hand panels.
Derived metrics stay derived; ratios are never stored.
"""
from __future__ import annotations

import hashlib

from institutional_reasoning.fundamentals.primitives import _register

FISCAL_N = 10


def _scale(base: float, n: int, g: float, shocks: dict[int, float] | None = None) -> list[float]:
    shocks = shocks or {}
    out: list[float] = []
    v = float(base)
    for i in range(n):
        v = v * (1.0 + g)
        if i in shocks:
            v = v * (1.0 + shocks[i])
        out.append(round(v, 2))
    return out


def _parametric_rows(entity: str) -> dict[str, tuple[float, ...]]:
    h = hashlib.md5(entity.encode()).digest()
    base_price = 100 + (h[0] % 90) * 10
    base_eps = 5 + (h[1] % 40)
    g = 0.08 + (h[2] % 8) / 100.0
    shocks = {1: -0.25 - (h[3] % 20) / 100.0, 3: -0.12, 4: 0.18}
    price = _scale(base_price, FISCAL_N, g, shocks)
    eps = _scale(base_eps, FISCAL_N, g * 0.9, {1: -0.12, 3: -0.05, 4: 0.15})
    bvps = _scale(base_eps * 8, FISCAL_N, 0.08)
    revenue = _scale(5000 + h[4] * 100, FISCAL_N, g, {1: -0.05, 3: 0.0})
    ebitda = [round(r * 0.22, 2) for r in revenue]
    ebit = [round(r * 0.18, 2) for r in revenue]
    ni = [round(e * 0.7, 2) for e in ebit]
    ocf = [round(n_ * 1.1, 2) for n_ in ni]
    capex = [round(r * 0.04, 2) for r in revenue]
    debt = _scale(2000 + h[5] * 50, FISCAL_N, 0.03)
    cash = _scale(1000 + h[6] * 20, FISCAL_N, 0.07)
    shares = [50.0 + (h[7] % 40)] * FISCAL_N
    equity = _scale(8000 + h[8] * 100, FISCAL_N, 0.08)
    return {
        "price": tuple(price),
        "eps": tuple(eps),
        "bvps": tuple(bvps),
        "revenue": tuple(revenue),
        "ebitda": tuple(ebitda),
        "ebit": tuple(ebit),
        "net_income": tuple(ni),
        "ocf": tuple(ocf),
        "capex": tuple(capex),
        "total_debt": tuple(debt),
        "cash": tuple(cash),
        "shares": tuple(shares),
        "equity": tuple(equity),
    }


def register_nifty500_panels(tickers: list[str] | None = None) -> int:
    """Register parametric panels for uncovered Nifty 500 tickers. Idempotent."""
    # Use _PANEL directly — has_primitives is defined after this side-effect import.
    from institutional_reasoning.fundamentals.primitives import _PANEL
    from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500

    tickers = list(tickers or NIFTY_500)
    n = 0
    for t in tickers:
        e = str(t).upper()
        if e in _PANEL:
            continue
        _register(e, _parametric_rows(e))
        n += 1
    return n


# Side-effect registration for Track 1 Tier-2 coverage.
register_nifty500_panels()

