"""Track 1 — parametric monthly returns for Nifty 500 Tier-2 names."""
from __future__ import annotations

import hashlib

from institutional_reasoning.fundamentals.market_series import _BENCHMARK, _IDIO, _MONTHLY_RETURNS, _mix


def _parametric_idio(entity: str) -> tuple[float, list[float]]:
    h = hashlib.md5(entity.encode()).digest()
    beta = round(0.7 + (h[0] % 70) / 100.0, 2)
    idio = []
    for i in range(len(_BENCHMARK)):
        # Deterministic residual in [-2.5, 2.5]
        v = ((h[i % 16] + h[(i + 3) % 16] * (i + 1)) % 500) / 100.0 - 2.5
        idio.append(round(v, 2))
    return beta, idio


def register_nifty500_returns(tickers: list[str] | None = None) -> int:
    from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500

    tickers = list(tickers or NIFTY_500)
    n = 0
    for t in tickers:
        e = str(t).upper()
        if e in _MONTHLY_RETURNS:
            continue
        beta, idio = _parametric_idio(e)
        _IDIO[e] = (beta, idio)
        _MONTHLY_RETURNS[e] = _mix(_BENCHMARK, idio, beta)
        n += 1
    return n


register_nifty500_returns()

