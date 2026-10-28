"""Primary regime fuse — deterministic priority (spec §2.1). Threshold-only for P0."""

from __future__ import annotations

from app.engines.e01.models.thresholds import AxisState


def fuse_primary_regime(axes: dict[str, AxisState]) -> str:
    """
    Priority: crisis > recession+risk_off > recovery > expansion+risk_on > slowdown
    > else composite label.
    """
    stress = axes["R_STRESS"].state
    vol = axes["R_VOL"].state
    cycle = axes["R_CYCLE"].state
    risk = axes["R_RISK"].state

    if stress == "crisis":
        return "crisis"
    if vol == "crisis_vol":
        return "crisis_vol"
    if cycle == "recession" and risk == "risk_off":
        return "recession_risk_off"
    if cycle == "recovery":
        return "recovery"
    if cycle == "expansion" and risk == "risk_on":
        return "expansion_risk_on"
    if cycle == "slowdown":
        return "slowdown"
    return f"{cycle}_{risk}"
