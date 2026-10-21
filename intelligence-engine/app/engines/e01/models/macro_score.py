"""MacroScore — spec §7.6 (threshold components only for P0)."""

from __future__ import annotations

from app.engines.e01.features.builder import FeatureVector
from app.engines.e01.models.thresholds import AxisState


def compute_macro_score(fv: FeatureVector, axes: dict[str, AxisState]) -> float:
    s_growth = _clip(_growth_score(fv, axes), -2, 2)
    s_liq = _clip(fv.get("liq_trend", 0.0) or 0.0, -2, 2)
    s_infl_stress = _clip(_infl_stress(fv, axes), -2, 2)
    s_risk = _clip(fv.get("risk_appetite", 0.0) or 0.0, -2, 2)
    s_stress = _clip((fv.get("stress_index", 0.0) or 0.0) * 2.0, -2, 2)
    s_policy_ease = _clip(_policy_ease(axes), -2, 2)

    composite = (
        0.25 * s_growth
        + 0.15 * s_liq
        - 0.15 * s_infl_stress
        + 0.20 * s_risk
        - 0.15 * s_stress
        + 0.10 * s_policy_ease
    )
    score = 50.0 + 10.0 * _clip(composite, -3, 3)
    return float(max(0.0, min(100.0, score)))


def _growth_score(fv: FeatureVector, axes: dict[str, AxisState]) -> float:
    if "growth_impulse" in fv.values:
        return fv.values["growth_impulse"]
    state = axes["R_CYCLE"].state
    return {"expansion": 1.0, "recovery": 0.5, "slowdown": -0.3, "recession": -1.5}.get(state, 0.0)


def _infl_stress(fv: FeatureVector, axes: dict[str, AxisState]) -> float:
    mom = fv.get("infl_momentum_us", 0.0) or 0.0
    if axes["R_INFL"].state == "inflationary":
        return max(mom, 1.0)
    if axes["R_INFL"].state == "deflationary_pressure":
        return 0.5
    return max(0.0, mom)


def _policy_ease(axes: dict[str, AxisState]) -> float:
    return {"easing": 1.0, "on_hold": 0.0, "tightening": -1.0}.get(axes["R_POLICY"].state, 0.0)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
