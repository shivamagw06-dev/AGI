"""Position size multiplier & vol target — spec §7.7."""

from __future__ import annotations

from app.engines.e01.models.thresholds import AxisState


def size_and_vol(axes: dict[str, AxisState]) -> tuple[float, float]:
    stress = axes["R_STRESS"].state
    vol = axes["R_VOL"].state
    risk = axes["R_RISK"].state

    if stress == "crisis" or vol == "crisis_vol":
        return 0.35, 0.06
    if vol == "high_vol":
        return 0.60, 0.08
    if risk == "risk_off":
        return 0.70, 0.09
    if risk == "risk_on" and vol == "low_vol":
        return 1.15, 0.12
    return 1.00, 0.10


def risk_level(stress_index: float | None) -> str:
    """risk_level ∈ low|moderate|elevated|critical from stress_index bands."""
    s = 0.0 if stress_index is None else stress_index
    if s < 0.35:
        return "low"
    if s < 0.55:
        return "moderate"
    if s < 0.70:
        return "elevated"
    return "critical"


def weight_adjustments(axes: dict[str, AxisState], size_mult: float) -> dict[str, float]:
    """P0 downstream weights (spec §10 contract keys)."""
    crisis = axes["R_STRESS"].state == "crisis" or axes["R_VOL"].state == "crisis_vol"
    risk_off = axes["R_RISK"].state == "risk_off" or axes["R_VOL"].state == "high_vol"
    risk_on = axes["R_RISK"].state == "risk_on" and axes["R_CYCLE"].state == "expansion"

    def scale(base: float, *, on: float, off: float, crisis_v: float) -> float:
        if crisis:
            return round(crisis_v, 2)
        if risk_off:
            return round(off, 2)
        if risk_on:
            return round(on, 2)
        return round(base, 2)

    return {
        "E03_xs_momentum": scale(1.0, on=1.10, off=0.75, crisis_v=0.40),
        "E04_stat_arb": scale(1.0, on=0.90, off=1.15, crisis_v=0.50),
        "E09_trend": scale(1.0, on=1.05 * min(size_mult, 1.2), off=0.70, crisis_v=0.35),
        "E08_short_vol_research": scale(1.0, on=0.70, off=0.50, crisis_v=0.20),
        "E08_tail_hedge_research": scale(1.0, on=1.00, off=1.20, crisis_v=1.40),
        "E02_value": scale(1.0, on=1.00, off=1.05, crisis_v=0.80),
        "E02_quality": scale(1.0, on=1.05, off=1.15, crisis_v=1.20),
        "E10_risk_parity": scale(1.0, on=1.00, off=1.05, crisis_v=1.10),
    }
