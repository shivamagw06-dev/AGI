"""Inverse-volatility seed weights (AM_INVVOL) — P0 baseline."""

from __future__ import annotations

from app.engines.e10.construction.select import Candidate


def inverse_volatility_weights(candidates: list[Candidate]) -> dict[str, float]:
    """w_i ∝ 1/σ_i, normalised to sum 1 over equity sleeve."""
    if not candidates:
        return {}
    inv = {c.symbol: 1.0 / max(c.sigma, 1e-6) for c in candidates}
    total = sum(inv.values())
    if total <= 0:
        n = len(candidates)
        return {c.symbol: 1.0 / n for c in candidates}
    return {sym: v / total for sym, v in inv.items()}
