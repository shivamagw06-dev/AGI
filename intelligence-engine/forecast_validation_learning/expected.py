"""Derive ExpectedOutcome from an IPCI Forecast Assessment snapshot."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import ExpectedOutcome

_SCENARIO_GROWTH = {
    "Bull": "up",
    "Base": "up",
    "Bear": "down",
}
_SCENARIO_MARGIN = {
    "Bull": "up",
    "Base": "stable",
    "Bear": "down",
}


def _blob(parts: list[Any]) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _direction_from_text(text: str, *, default: str) -> str:
    if any(k in text for k in ("margin expansion", "expanding margin", "margin up", "nim expansion")):
        # handled by margin caller
        pass
    if any(k in text for k in ("contract", "slowdown", "decline", "compression", "weak demand", "recession")):
        return "down"
    if any(k in text for k in ("accelerate", "strong growth", "reacceleration", "robust demand", "expansion")):
        return "up"
    if any(k in text for k in ("stable", "steady", "inline", "range-bound", "moderate")):
        return "stable"
    return default


def extract_expected(assessment: dict[str, Any]) -> ExpectedOutcome:
    """Freeze expected outcome fields from a published assessment."""
    dist = {
        p.get("scenario"): int(p.get("probability_pct") or 0)
        for p in (assessment.get("probabilities") or [])
        if p.get("scenario")
    }
    if not dist and assessment.get("distribution"):
        raw = assessment["distribution"]
        # distribution may be {Bull: {probability_pct}} or {Bull: int}
        for k, v in raw.items():
            if isinstance(v, dict):
                dist[k] = int(v.get("probability_pct") or 0)
            else:
                dist[k] = int(v)

    if dist:
        modal = max(dist, key=dist.get)  # type: ignore[arg-type]
    else:
        modal = "Base"
        dist = {"Bull": 25, "Base": 50, "Bear": 25}

    confidence = 0
    conf = assessment.get("confidence") or {}
    if isinstance(conf, dict):
        confidence = int(conf.get("overall_pct") or 0)
    if not confidence:
        # per-scenario average
        assessments = assessment.get("assessments") or []
        if assessments:
            confidence = int(
                round(sum(int(a.get("confidence_pct") or 0) for a in assessments) / len(assessments))
            )

    narratives: list[str] = []
    catalysts: list[str] = []
    for a in assessment.get("assessments") or []:
        if a.get("scenario") == modal:
            narratives.extend(list(a.get("narrative") or []))
            for c in a.get("catalysts") or []:
                if isinstance(c, dict):
                    catalysts.append(str(c.get("label") or c.get("name") or c.get("catalyst") or c))
                else:
                    catalysts.append(str(c))
        for m in a.get("missing_evidence") or []:
            # Missing evidence often names catalysts we care about validating later
            if isinstance(m, str) and m not in catalysts and "guidance" in m.lower():
                catalysts.append(m)

    # Also pull missing_evidence from top-level as potential catalyst watchlist
    for m in assessment.get("missing_evidence") or []:
        if isinstance(m, str) and m not in catalysts:
            catalysts.append(m)

    text = _blob(narratives + catalysts + [assessment.get("entity"), assessment.get("note")])
    growth = _direction_from_text(text, default=_SCENARIO_GROWTH.get(modal, "stable"))
    margin_default = _SCENARIO_MARGIN.get(modal, "stable")
    if any(k in text for k in ("margin expansion", "expanding margin", "nim expansion")):
        margin = "up"
    elif any(k in text for k in ("margin compression", "margin pressure", "cost inflation")):
        margin = "down"
    else:
        margin = margin_default

    timing = "medium"
    if any(k in text for k in ("near term", "this quarter", "imminent")):
        timing = "near"
    elif any(k in text for k in ("multi-year", "structural", "long term")):
        timing = "long"

    summary = narratives[0] if narratives else f"Modal scenario {modal} with Base/Bull/Bear distribution frozen."

    return ExpectedOutcome(
        modal_scenario=modal,
        probability_distribution={str(k): int(v) for k, v in dist.items()},
        confidence_pct=confidence,
        growth_direction=growth,
        margin_direction=margin,
        catalysts=catalysts[:12],
        timing_horizon=timing,
        narrative_summary=summary[:400],
        metrics={
            "overall_forecast_quality_pct": assessment.get("overall_forecast_quality_pct"),
            "scope": assessment.get("scope"),
        },
    )
