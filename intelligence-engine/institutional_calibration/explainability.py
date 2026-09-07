"""Explainability engine — every recommendation answers why / why not / what changes."""

from __future__ import annotations

from typing import Sequence

from institutional_calibration.models import Calibration, DecisionExplainability, DecisionScorecard
from institutional_decision.models import InstitutionalDecision
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.reasoning import Reason
from institutional_calibration.schema import EXPLAINABILITY_VERSION


def build_explainability(
    decision: InstitutionalDecision,
    reasons: Sequence[Reason],
    evidence: InstitutionalReportInput,
    calibration: Calibration,
    scorecard: DecisionScorecard,
) -> DecisionExplainability:
    rec = str(decision.recommendation or "").upper()
    supporting = list(decision.supporting_reasons or ())
    contradicting = list(decision.contradicting_reasons or ())
    unknowns = list(decision.unknowns or ())
    upgrades = list(decision.upgrade_conditions or ())
    downgrades = list(decision.downgrade_conditions or ())

    why_buy: list[str] = []
    why_hold: list[str] = []
    why_sell: list[str] = []
    why_not_buy: list[str] = []
    why_not_sell: list[str] = []

    bq = evidence.business_quality
    fq = str(evidence.financial_quality or "")
    val = str(evidence.valuation or "")
    risk = str(evidence.overall_risk or "")

    quality_stack = f"business_quality={bq}; financial_quality={fq}"
    val_risk = f"valuation={val}; overall_risk={risk}"

    if rec == "BUY":
        why_buy = supporting[:6] or [quality_stack, val_risk, f"score={decision.score}"]
        why_not_sell = [
            "Quality / valuation / risk stack does not meet SELL thresholds",
            *supporting[:3],
        ]
        why_not_buy = []  # N/A — is BUY
        why_hold = contradicting[:3] or ["Residual risks remain monitored"]
        why_sell = contradicting[:3]
    elif rec == "SELL":
        why_sell = contradicting[:6] or [quality_stack, val_risk, f"score={decision.score}"]
        why_not_buy = [
            "Quality / valuation / risk stack does not meet BUY thresholds",
            *contradicting[:3],
        ]
        why_not_sell = []
        why_hold = supporting[:3] or ["Some franchise strengths remain"]
        why_buy = supporting[:3]
    else:  # HOLD
        why_hold = supporting[:6] or [quality_stack, val_risk, f"score={decision.score}"]
        why_not_buy = [
            "Score below BUY threshold",
            *contradicting[:3],
            val_risk,
        ]
        why_not_sell = [
            "Score above SELL threshold",
            *supporting[:3],
            quality_stack,
        ]
        why_buy = [c for c in upgrades[:4]] or supporting[:2]
        why_sell = [c for c in downgrades[:4]] or contradicting[:2]

    increased = [c.label for c in calibration.positive_contributors] + [
        c.label for c in calibration.bonuses
    ]
    reduced = [c.label for c in calibration.negative_contributors] + [
        c.label for c in calibration.penalties
    ]

    # Scorecard pressures / supports
    for line in scorecard.lines:
        if line.points <= -6:
            reduced.append(f"{line.dimension} ({line.points})")
        elif line.points >= 12:
            increased.append(f"{line.dimension} ({line.points:+d})")

    what_would_change = list(dict.fromkeys([*upgrades[:4], *downgrades[:4], *unknowns[:3]]))
    if not what_would_change:
        what_would_change = [
            "Material change in valuation band",
            "Sustained shift in financial quality",
            "Resolution of listed unknowns",
        ]

    # Reason titles for richness
    for r in reasons:
        if r.conclusion and r.section_key in {"valuation", "risk_assessment"} and rec == "HOLD":
            if r.conclusion not in why_not_buy:
                why_not_buy.append(r.conclusion)

    return DecisionExplainability(
        why_buy=why_buy[:8],
        why_hold=why_hold[:8],
        why_sell=why_sell[:8],
        why_not_buy=why_not_buy[:8],
        why_not_sell=why_not_sell[:8],
        what_reduced_confidence=list(dict.fromkeys(reduced))[:10],
        what_increased_confidence=list(dict.fromkeys(increased))[:10],
        what_would_change=what_would_change[:10],
    )


def explainability_meta() -> dict:
    return {"explainability_version": EXPLAINABILITY_VERSION}
