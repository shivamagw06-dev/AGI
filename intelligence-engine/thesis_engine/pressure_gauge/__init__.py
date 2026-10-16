"""Thesis pressure gauge — actionable stress independent of confidence."""

from __future__ import annotations

from typing import Any

_PRESSURE_NAMES = {
    "Competitive Position": "Peer Deterioration",
    "Macro Alignment": "Macro Deterioration",
    "Valuation": "Valuation Expansion",
    "Financial Quality": "Financial / Accounting",
    "Business Quality": "Business Deterioration",
    "Capital Allocation": "Management / Capital Allocation",
    "Portfolio Fit": "Portfolio Concentration",
}


def build_pressure_gauge(
    pillars: list[dict[str, Any]],
    contradictions: dict[str, Any],
) -> dict[str, Any]:
    raw_components: dict[str, float] = {}
    pillar_rows = []
    for p in pillars:
        strength = float(p.get("strength") or 0.5)
        contradiction_pressure = min(0.25, 0.06 * len(p.get("contradictions") or []))
        pressure = max(0.0, (0.62 - strength) * 1.4) + contradiction_pressure
        raw_components[_PRESSURE_NAMES[p["pillar"]]] = max(0.0, pressure)
        score = round(min(100.0, max(0.0, pressure * 100)), 1)
        pillar_rows.append(
            {
                "pillar": p["pillar"],
                "driver": _PRESSURE_NAMES[p["pillar"]],
                "pressure_score": score,
                "level": (
                    "Healthy"
                    if score < 20
                    else "Watch"
                    if score < 40
                    else "Pressure"
                    if score < 65
                    else "Critical"
                ),
            }
        )

    unresolved = len(contradictions.get("outstanding_questions") or [])
    raw_components["Unresolved Contradictions"] = min(0.4, unresolved * 0.035)
    raw_total = sum(raw_components.values())
    # Bounded aggregate; normalize components so their displayed sum equals score.
    score = round(100.0 * raw_total / (raw_total + 1.4), 1) if raw_total else 0.0
    components = {
        k: round(score * v / raw_total, 1) if raw_total else 0.0
        for k, v in raw_components.items()
    }
    # Fix rounding reconciliation on the final component.
    if components:
        last = next(reversed(components))
        components[last] = round(components[last] + score - sum(components.values()), 1)

    level = (
        "Low"
        if score < 25
        else "Moderate"
        if score < 50
        else "High"
        if score < 75
        else "Critical"
    )
    pressured = [p for p in pillar_rows if p["level"] in ("Pressure", "Critical")]
    return {
        "score": score,
        "level": level,
        "components": components,
        "pillars": pillar_rows,
        "pressured_pillars": [p["pillar"] for p in pressured],
        "unresolved_contradictions": unresolved,
        "message": (
            "The thesis is intact, but "
            + " and ".join(p["pillar"].lower() for p in pressured)
            + " are applying pressure."
            if pressured
            else "The thesis is intact with no major pillar under pressure."
        ),
        "separate_from_confidence": True,
    }
