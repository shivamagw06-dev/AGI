"""E04-002 Relative Value State Builder."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e04.features.builder import PairPanel
from app.engines.e04.mapping import Z_CHEAP, Z_RICH
from app.engines.e04.models.stats import engle_granger, half_life, ols_hedge, spread_series, zscore


@dataclass
class RelativeValueRow:
    pair_id: str
    leg_a: str
    leg_b: str
    as_of: str
    sector_id: str | None
    hedge_alpha: float
    hedge_beta: float
    r_squared: float
    spread: float
    spread_mean: float
    spread_std: float
    z_score: float
    cointegrated: bool
    adf_stat: float
    half_life: float | None
    mispricing_score: float
    mean_reversion_signal: float
    composite_score: float
    label: str
    side: str  # long_spread|short_spread|flat
    confidence: float
    discovery: str
    stale_inputs: list[str] = field(default_factory=list)
    rval_meta: dict[str, float] = field(default_factory=dict)


def compute_pair_states(panels: dict[str, PairPanel]) -> dict[str, RelativeValueRow]:
    out: dict[str, RelativeValueRow] = {}
    for pid in sorted(panels.keys()):
        panel = panels[pid]
        # OLS: leg_a ~ alpha + beta * leg_b  (y=A, x=B)
        ols = ols_hedge(panel.closes_a, panel.closes_b)
        spr = spread_series(panel.closes_a, panel.closes_b, ols.alpha, ols.beta)
        if not spr:
            continue
        # Optional RVAL_SPREAD override for latest level only (still compute z from series)
        if "RVAL_SPREAD" in panel.rval_meta:
            spr = list(spr)
            spr[-1] = panel.rval_meta["RVAL_SPREAD"]
        z, mu, sigma = zscore(spr)
        eg = engle_granger(ols.residuals if ols.residuals else spr)
        if "RVAL_COINTEGRATION" in panel.rval_meta:
            # External metadata: treat >0.5 as cointegrated flag proxy
            eg_coint = panel.rval_meta["RVAL_COINTEGRATION"] >= 0.5
            cointegrated = bool(eg_coint)
            adf_stat = eg.adf_stat
        else:
            cointegrated = eg.cointegrated
            adf_stat = eg.adf_stat
        hl = half_life(spr)
        half = hl.half_life
        if "RVAL_HALF_LIFE" in panel.rval_meta and panel.rval_meta["RVAL_HALF_LIFE"] > 0:
            half = float(panel.rval_meta["RVAL_HALF_LIFE"])

        mispricing = min(100.0, abs(z) * 25.0)  # |z|=4 → 100
        # Mean-reversion signal: fade spread (negative z ⇒ long spread)
        mr_signal = round(-z, 8)
        label, side = _label_side(z, cointegrated)
        # Composite: mispricing + coint boost + half-life quality − stale penalty
        hl_term = 0.0
        if half is not None and 1.0 <= half <= 60.0:
            hl_term = 20.0 * (1.0 - abs(half - 10.0) / 50.0)
        coint_term = 25.0 if cointegrated else 5.0
        composite = round(
            max(0.0, min(100.0, 0.45 * mispricing + coint_term + hl_term + 0.10 * ols.r_squared * 100.0)),
            6,
        )
        coverage = 1.0 - 0.15 * len(panel.stale)
        conf = round(
            max(
                0.35,
                min(
                    0.95,
                    0.45
                    + 0.25 * (1.0 if cointegrated else 0.0)
                    + 0.15 * ols.r_squared
                    + 0.15 * max(0.0, coverage)
                    - 0.05 * min(3.0, abs(z) / 2.0),
                ),
            ),
            6,
        )
        out[pid] = RelativeValueRow(
            pair_id=pid,
            leg_a=panel.leg_a,
            leg_b=panel.leg_b,
            as_of=panel.as_of,
            sector_id=panel.sector_id,
            hedge_alpha=ols.alpha,
            hedge_beta=ols.beta,
            r_squared=ols.r_squared,
            spread=round(spr[-1], 10),
            spread_mean=mu,
            spread_std=sigma,
            z_score=z,
            cointegrated=cointegrated,
            adf_stat=adf_stat,
            half_life=half,
            mispricing_score=round(mispricing, 6),
            mean_reversion_signal=mr_signal,
            composite_score=composite,
            label=label,
            side=side,
            confidence=conf,
            discovery=panel.discovery,
            stale_inputs=list(panel.stale),
            rval_meta=dict(panel.rval_meta),
        )
    return out


def _label_side(z: float, cointegrated: bool) -> tuple[str, str]:
    if not cointegrated and abs(z) < 1.0:
        return "Non-Cointegrated", "flat"
    if z >= Z_RICH:
        return "Rich", "short_spread"
    if z <= Z_CHEAP:
        return "Cheap", "long_spread"
    if z >= 0.75:
        return "Mildly Rich", "short_spread"
    if z <= -0.75:
        return "Mildly Cheap", "long_spread"
    return "Fair", "flat"
