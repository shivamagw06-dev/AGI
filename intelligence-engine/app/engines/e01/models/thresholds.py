"""Threshold Regime Classifier — P0 only (spec §7.4). No HMM/ML."""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.e01.features.builder import FeatureVector


@dataclass(frozen=True)
class AxisState:
    state: str
    confidence: float


def classify_axes(
    fv: FeatureVector,
    *,
    prior_cycle: str | None = None,
) -> dict[str, AxisState]:
    """Deterministic threshold classifiers for all nine axes."""
    return {
        "R_VOL": _r_vol(fv),
        "R_CYCLE": _r_cycle(fv, prior_cycle=prior_cycle),
        "R_RISK": _r_risk(fv),
        "R_STRESS": _r_stress(fv),
        "R_INFL": _r_infl(fv),
        "R_LIQ": _r_liq(fv),
        "R_POLICY": _r_policy(fv),
        "R_MARKET": _r_market(fv),
        "R_EARN": _r_earn(fv),
    }


def _r_vol(fv: FeatureVector) -> AxisState:
    stress = fv.get("stress_index", 0.0) or 0.0
    vix = fv.get("vix_pctile_5y")
    if vix is None:
        return AxisState("normal_vol", 0.4)
    if stress >= 0.85 or vix >= 0.95:
        return AxisState("crisis_vol", _conf(vix, 0.95, high=True))
    if vix >= 0.75:
        return AxisState("high_vol", _conf(vix, 0.75, high=True))
    if vix <= 0.25:
        return AxisState("low_vol", _conf(0.25 - vix, 0.25, high=True))
    return AxisState("normal_vol", 0.66)


def _r_cycle(fv: FeatureVector, *, prior_cycle: str | None) -> AxisState:
    pmi_us = fv.get("pmi_us")
    pmi_in = fv.get("pmi_in")
    growth = fv.get("growth_impulse")
    if pmi_us is None and pmi_in is None and growth is None:
        return AxisState("slowdown", 0.35)

    z_us = ((pmi_us - 50.0) / 5.0) if pmi_us is not None else 0.0
    z_in = ((pmi_in - 50.0) / 5.0) if pmi_in is not None else 0.0
    gi = growth if growth is not None else 0.0
    # Spec example: growth = 0.5*z(pmi_us)+0.5*z(pmi_in)+0.25*growth_impulse
    g = 0.5 * z_us + 0.5 * z_in + 0.25 * gi

    if (
        g > 0.5
        and (pmi_us is None or pmi_us > 50)
        and (pmi_in is None or pmi_in > 50)
    ):
        return AxisState("expansion", min(0.9, 0.55 + abs(g) * 0.1))
    if g < -0.7 or (pmi_us is not None and pmi_us < 47):
        return AxisState("recession", min(0.9, 0.55 + abs(g) * 0.1))
    if prior_cycle in {"recession", "slowdown"} and g > 0:
        return AxisState("recovery", 0.6)
    return AxisState("slowdown", 0.55)


def _r_risk(fv: FeatureVector) -> AxisState:
    ra = fv.get("risk_appetite")
    if ra is None:
        return AxisState("risk_mixed", 0.4)
    if ra > 0.5:
        return AxisState("risk_on", min(0.9, 0.55 + ra * 0.15))
    if ra < -0.5:
        return AxisState("risk_off", min(0.9, 0.55 + abs(ra) * 0.15))
    return AxisState("risk_mixed", 0.55)


def _r_stress(fv: FeatureVector) -> AxisState:
    stress = fv.get("stress_index", 0.0) or 0.0
    vix = fv.get("vix_pctile_5y", 0.0) or 0.0
    if stress >= 0.85 or vix >= 0.95:
        return AxisState("crisis", min(0.95, 0.6 + stress * 0.3))
    if stress >= 0.7 or vix >= 0.85:
        return AxisState("elevated_stress", 0.65)
    return AxisState("normal", 0.75)


def _r_infl(fv: FeatureVector) -> AxisState:
    mom = fv.get("infl_momentum_us")
    oil = fv.get("oil_mom_63d", 0.0) or 0.0
    if mom is None:
        return AxisState("stable_prices", 0.4)
    # Oil shock flag note from spec
    if oil > 0.25 and mom > 0:
        return AxisState("inflationary", 0.7)
    if mom > 1.0:
        return AxisState("inflationary", min(0.9, 0.55 + mom * 0.1))
    if mom < -0.5:
        return AxisState("disinflationary", min(0.85, 0.55 + abs(mom) * 0.1))
    if mom < -1.5:
        return AxisState("deflationary_pressure", 0.7)
    return AxisState("stable_prices", 0.6)


def _r_liq(fv: FeatureVector) -> AxisState:
    liq = fv.get("liq_trend")
    if liq is None:
        return AxisState("liq_neutral", 0.4)
    if liq > 0.5:
        return AxisState("liq_expansion", min(0.85, 0.55 + liq * 0.1))
    if liq < -0.5:
        return AxisState("liq_contraction", min(0.85, 0.55 + abs(liq) * 0.1))
    return AxisState("liq_neutral", 0.55)


def _r_policy(fv: FeatureVector) -> AxisState:
    vel = fv.get("policy_velocity_us")
    if vel is None:
        return AxisState("on_hold", 0.5)
    if vel < -0.25:
        return AxisState("easing", 0.65)
    if vel > 0.25:
        return AxisState("tightening", 0.65)
    return AxisState("on_hold", 0.7)


def _r_market(fv: FeatureVector) -> AxisState:
    # Proxy: risk appetite + growth; P0 threshold (no equity trend model yet)
    ra = fv.get("risk_appetite", 0.0) or 0.0
    gi = fv.get("growth_impulse", 0.0) or 0.0
    signal = 0.6 * ra + 0.4 * gi
    if signal > 0.5:
        return AxisState("bull", min(0.85, 0.55 + signal * 0.15))
    if signal < -0.5:
        return AxisState("bear", min(0.85, 0.55 + abs(signal) * 0.15))
    return AxisState("sideways", 0.55)


def _r_earn(fv: FeatureVector) -> AxisState:
    dens = fv.get("earn_density")
    if dens is None:
        return AxisState("post_earnings", 0.5)
    if dens >= 1.2:
        return AxisState("earnings_season", 0.75)
    if dens >= 0.8:
        return AxisState("pre_earnings", 0.65)
    return AxisState("post_earnings", 0.8)


def _conf(distance: float, threshold: float, *, high: bool) -> float:
    mag = abs(distance) if high else abs(threshold)
    return max(0.45, min(0.95, 0.55 + mag * 0.2))
