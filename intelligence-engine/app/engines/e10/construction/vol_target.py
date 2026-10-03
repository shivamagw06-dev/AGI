"""Volatility targeting scale (AM_VOLTARGET) — diagonal cov approximation for P0."""

from __future__ import annotations

import math

from app.contracts.engine_state import EngineState
from app.engines.e10.construction.select import Candidate
from app.engines.e10.mapping import DEFAULT_VOL_TARGET


def resolve_vol_target(e14: EngineState | None) -> float:
    if e14 is None:
        return DEFAULT_VOL_TARGET
    meta = e14.metadata or {}
    suggested = meta.get("vol_target_suggested")
    if suggested is not None:
        return float(max(0.03, min(0.40, float(suggested))))
    return DEFAULT_VOL_TARGET


def size_multipliers(e14: EngineState | None) -> tuple[float, float]:
    """Return (e01_size_mult placeholder via e14 metadata if present, e14_size_mult)."""
    if e14 is None:
        return 1.0, 1.0
    meta = e14.metadata or {}
    e14_mult = float(meta.get("size_multiplier") or 1.0)
    e01_mult = float(meta.get("e01_size_multiplier") or meta.get("size_multiplier_e01") or 1.0)
    return max(0.05, min(1.0, e01_mult)), max(0.05, min(1.0, e14_mult))


def portfolio_volatility(weights: dict[str, float], candidates: list[Candidate]) -> float:
    """σ_p ≈ sqrt(Σ w_i² σ_i²) — diagonal covariance (P0, no full cov estimator)."""
    sig = {c.symbol: c.sigma for c in candidates}
    var = 0.0
    for sym, w in weights.items():
        s = sig.get(sym, 0.25)
        var += (w * s) ** 2
    return float(math.sqrt(max(var, 0.0)))


def apply_vol_target(
    equity_weights: dict[str, float],
    candidates: list[Candidate],
    *,
    vol_target: float,
    e14: EngineState | None,
) -> tuple[dict[str, float], float, float, list[str]]:
    """
    Scale equity sleeve: w' = w * min(1, σ_tgt/σ_p) * size_mults.
    Returns (scaled_weights, expected_vol, scale, binding).
    """
    binding: list[str] = []
    if not equity_weights:
        return {}, 0.0, 0.0, binding

    sigma_p = portfolio_volatility(equity_weights, candidates)
    e01_m, e14_m = size_multipliers(e14)
    scale = 1.0
    if sigma_p > 1e-9:
        scale = min(1.0, vol_target / sigma_p)
    if scale < 1.0 - 1e-9:
        binding.append("C_VOL_TARGET")
    scale *= e01_m * e14_m
    if e01_m * e14_m < 1.0 - 1e-9:
        binding.append("C_SIZE_MULT")

    scaled = {s: w * scale for s, w in equity_weights.items()}
    exp_vol = portfolio_volatility(scaled, candidates)
    return scaled, round(exp_vol, 6), round(scale, 6), binding
