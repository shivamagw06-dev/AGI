"""Internal ICI object builders — opinions only, no engines/providers."""

from __future__ import annotations

from typing import Any


def committee_consensus(
    *,
    agreements: list[str],
    disagreements: list[str],
    weak_evidence: list[str],
    needing_review: list[str],
    stances: dict[str, str],
) -> dict[str, Any]:
    return {
        "type": "CommitteeConsensus",
        "areas_of_agreement": agreements,
        "areas_of_disagreement": disagreements,
        "areas_with_weak_evidence": weak_evidence,
        "areas_needing_review": needing_review,
        "stances": stances,
    }


def committee_conflict(
    *,
    topic: str,
    left: dict[str, str],
    right: dict[str, str],
    assessment: str,
    confidence_impact: str,
) -> dict[str, Any]:
    return {
        "type": "CommitteeConflict",
        "topic": topic,
        "left": left,
        "right": right,
        "tension": f"{left.get('view', '')} vs {right.get('view', '')}".strip(),
        "committee_assessment": assessment,
        "recommendation_confidence_impact": confidence_impact,
    }


def committee_challenge(
    *,
    target_role: str,
    target_analyst: str,
    claim: str,
    challenge: str,
    need: str,
) -> dict[str, Any]:
    return {
        "type": "CommitteeChallenge",
        "target_role": target_role,
        "target_analyst": target_analyst,
        "claim": claim,
        "challenge": challenge,
        "need": need,
        "open_evidence_request": {
            "type": "OpenEvidenceRequest",
            "for_analyst": target_analyst,
            "request": need,
            "related_claim": claim,
        },
    }


def committee_question(*, text: str, owner: str = "committee", priority: str = "normal") -> dict[str, Any]:
    return {"type": "CommitteeQuestion", "text": text, "owner": owner, "priority": priority}


def committee_vote(
    *,
    ballots: dict[str, str],
    consensus: str,
    conviction: str,
    tally: str,
    constructive: int,
    neutral: int,
    cautious: int,
    abstain: int,
) -> dict[str, Any]:
    return {
        "type": "CommitteeVote",
        "ballots": ballots,
        "consensus": consensus,
        "conviction": conviction,
        "tally": tally,
        "counts": {
            "constructive": constructive,
            "neutral": neutral,
            "cautious": cautious,
            "abstain": abstain,
        },
    }


def minority_opinion(*, view: str, supporters: list[str], weight: str = "minority") -> dict[str, Any]:
    return {
        "type": "MinorityOpinion",
        "view": view,
        "supporters": supporters,
        "weight": weight,
    }


def committee_decision(
    *,
    business_quality: str,
    financials: str,
    valuation: str,
    risk: str,
    committee_position: str,
    recommendation_readiness: str,
    confidence: float,
    macro: str = "Neutral",
    market: str = "Neutral",
) -> dict[str, Any]:
    return {
        "type": "CommitteeDecision",
        "business_quality": business_quality,
        "financials": financials,
        "valuation": valuation,
        "risk": risk,
        "macro": macro,
        "market": market,
        "committee_position": committee_position,
        "recommendation_readiness": recommendation_readiness,
        "confidence": confidence,
        # Explicitly not Buy/Hold/Sell
        "not_a_trade_ticket": True,
    }


def committee_minutes(**fields: Any) -> dict[str, Any]:
    return {"type": "CommitteeMinutes", **fields}


def committee_accuracy(
    *,
    accuracy_pct: float | None,
    predictions_scored: int = 0,
    note: str = "",
) -> dict[str, Any]:
    return {
        "type": "CommitteeAccuracy",
        "committee_accuracy_pct": accuracy_pct,
        "predictions_scored": predictions_scored,
        "note": note
        or (
            f"Committee accuracy {accuracy_pct}% on reviewed expectations."
            if accuracy_pct is not None
            else "No scored predictions yet — accountability accumulates over meetings."
        ),
    }
