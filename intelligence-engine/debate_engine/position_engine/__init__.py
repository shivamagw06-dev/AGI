"""Position engine — one explicit, evidenced position per analyst."""

from __future__ import annotations

from typing import Any

from debate_engine.schema import ANALYSTS, POSITION_SCORES

_PILLAR_BY_ANALYST = {
    "Business": "Business Quality",
    "Financial": "Financial Quality",
    "Valuation": "Valuation",
    "Risk": "Portfolio Fit",
    "Macro": "Macro Alignment",
    "Portfolio": "Portfolio Fit",
    "Management": "Capital Allocation",
}


def _position(strength: float, analyst: str) -> str:
    # Risk functions as a challenger: invert high thesis strength into lower concern.
    if analyst == "Risk":
        if strength >= 0.72:
            return "Neutral"
        if strength >= 0.55:
            return "Concern"
        return "Strong Concern"
    if strength >= 0.82:
        return "Strong Support"
    if strength >= 0.6:
        return "Support"
    if strength >= 0.48:
        return "Neutral"
    if strength >= 0.36:
        return "Concern"
    if strength >= 0.22:
        return "Strong Concern"
    return "Reject"


def build_positions(
    thesis: dict[str, Any],
    supplied_opinions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    pillars = {p.get("pillar"): p for p in (thesis.get("supporting_pillars") or [])}
    supplied = {str(x.get("analyst")): x for x in (supplied_opinions or [])}
    positions = []
    for analyst in ANALYSTS:
        pillar_name = _PILLAR_BY_ANALYST[analyst]
        pillar = pillars.get(pillar_name) or {}
        strength = float(pillar.get("strength") or 0.5)
        confidence = float(pillar.get("confidence") or thesis.get("confidence") or 0.55)
        custom = supplied.get(analyst) or {}
        position = str(custom.get("position") or _position(strength, analyst))

        support = list(custom.get("supporting_evidence") or pillar.get("evidence") or [])
        oppose = list(custom.get("contradicting_evidence") or pillar.get("contradictions") or [])
        missing = list(pillar.get("missing_evidence") or thesis.get("missing_evidence") or [])
        assumptions = [
            f"{pillar_name} remains within its current evidence range",
            f"No structural break invalidates {pillar_name.lower()}",
        ]
        if analyst == "Valuation":
            assumptions[0] = "Current quality is not already fully priced"
        elif analyst == "Macro":
            assumptions[0] = "The macro regime remains compatible with the thesis"
        elif analyst == "Business":
            assumptions[0] = "The competitive moat remains durable"
        elif analyst == "Risk":
            assumptions[0] = "Identified downside scenarios remain containable"

        open_questions = [
            f"What evidence would move {analyst} from {position}?",
            f"Is {pillar_name} robust under the thesis-breaking scenario?",
        ]
        positions.append(
            {
                "analyst": analyst,
                "pillar": pillar_name,
                "position": position,
                "position_score": POSITION_SCORES[position],
                "conclusion": (
                    custom.get("conclusion")
                    or f"{pillar_name} is {pillar.get('verdict', 'Neutral').lower()} and warrants a {position.lower()} stance."
                ),
                "supporting_evidence": support[:5],
                "contradicting_evidence": oppose[:4],
                "confidence": round(float(custom.get("confidence") or confidence), 4),
                "confidence_pct": round(float(custom.get("confidence") or confidence) * 100),
                "assumptions": list(custom.get("assumptions") or assumptions),
                "open_questions": list(custom.get("open_questions") or open_questions),
                "required_evidence": list(
                    custom.get("required_evidence")
                    or missing
                    or [f"Updated evidence for {pillar_name}"]
                )[:5],
                "revision_count": 0,
            }
        )
    return positions
