"""Module 2 — Applicability Engine.

Scores which frameworks apply before execution.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.confidence import confidence_for
from institutional_reasoning.iki.registry import frameworks_for_question_type, get_framework
from institutional_reasoning.iki.schema import ApplicabilityScore

APPLICABILITY_VERSION = "applicability-engine-v1.0.0"

BANK_TICKERS = frozenset(
    {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN", "NIFTYBANK"}
)
INSURANCE_TICKERS = frozenset({"HDFCLIFE", "SBILIFE", "ICICIPRULI"})
GROWTH_INTERNET = frozenset({"ZOMATO", "ETERNAL", "SWIGGY", "NYKAA", "PAYTM"})
IT_TICKERS = frozenset({"INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "NIFTYIT"})


def infer_sector(entity_id: str | None, entity_type: str | None = None) -> str | None:
    eid = str(entity_id or "").upper()
    if eid in BANK_TICKERS or "BANK" in eid:
        return "bank"
    if eid in INSURANCE_TICKERS:
        return "insurance"
    if eid in GROWTH_INTERNET:
        return "consumer_internet"
    if eid in IT_TICKERS:
        return "it_services"
    if str(entity_type or "") == "Index":
        return "index"
    return None


def _base_score(spec, *, question_type: str, entity_type: str, sector: str | None) -> ApplicabilityScore:
    fid = spec.framework_id
    reasons: list[str] = []
    score = float(spec.priority)

    if question_type and question_type not in spec.question_types and spec.question_types:
        score -= 40
        reasons.append(f"Question type '{question_type}' outside primary types")

    if entity_type and entity_type in spec.not_applicable_entity_types:
        return ApplicabilityScore(
            framework_id=fid,
            score=0.0,
            applicable=False,
            reasons=[f"Not applicable for entity type {entity_type}"],
            alternatives=list(spec.alternative_frameworks),
            confidence_band=confidence_for(fid)["band"],
        )

    if sector and sector in spec.not_applicable_sectors:
        alts = list(spec.alternative_frameworks) or list(spec.competing_frameworks)[:1]
        reason = f"Not applicable for sector '{sector}'"
        if fid in {"dcf_applicability", "dcf_fcff"} and sector in {"bank", "insurance", "nbfc"}:
            reason = "Financial institution — DCF is the wrong primary model"
            alts = ["residual_income"] if "residual_income" not in alts else alts
        return ApplicabilityScore(
            framework_id=fid,
            score=0.0,
            applicable=False,
            reasons=[reason],
            alternatives=alts,
            confidence_band=confidence_for(fid)["band"],
        )

    if spec.applicable_sectors and sector and sector not in spec.applicable_sectors:
        # residual income prefers banks but can still score low elsewhere
        if fid == "residual_income" and sector not in spec.applicable_sectors:
            score -= 25
            reasons.append(f"Residual income preferred for FI; sector={sector}")

    if spec.applicable_sectors and sector and sector in spec.applicable_sectors:
        score += 15
        reasons.append(f"Preferred for sector '{sector}'")

    if entity_type and spec.applicable_entity_types and entity_type not in spec.applicable_entity_types:
        score -= 30
        reasons.append(f"Entity type {entity_type} weakly matched")

    # Growth / Graham conflict
    if sector == "consumer_internet" and spec.school == "graham":
        return ApplicabilityScore(
            framework_id=fid,
            score=0.0,
            applicable=False,
            reasons=["Graham rejects speculative growth without asset/earnings floor"],
            alternatives=["rel_val_damodaran", "dcf_fcff"],
            confidence_band=confidence_for(fid)["band"],
        )
    if sector == "consumer_internet" and fid == "buffett_quality":
        return ApplicabilityScore(
            framework_id=fid,
            score=35.0,
            applicable=False,
            reasons=["Buffett wonderful-business screen rejects pre-moat consumer internet by default"],
            alternatives=["rel_val_damodaran", "business_quality_roic"],
            confidence_band=confidence_for(fid)["band"],
        )
    if sector == "consumer_internet" and fid in {"rel_val_damodaran", "dcf_fcff", "dcf_applicability"}:
        score += 10
        reasons.append("Growth / relative frameworks preferred for consumer internet")

    cal = confidence_for(fid)
    score = score * float(cal.get("weight_multiplier") or 0.8)
    score = max(0.0, min(100.0, score))
    applicable = score >= 45.0
    if not reasons:
        reasons.append("Matches question type and entity constraints")
    return ApplicabilityScore(
        framework_id=fid,
        score=round(score, 1),
        applicable=applicable,
        reasons=reasons,
        alternatives=list(spec.alternative_frameworks),
        confidence_band=str(cal.get("band") or "Medium"),
    )


def score_applicability(
    *,
    question_type: str,
    entity_id: str | None,
    entity_type: str | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    sector = sector or infer_sector(entity_id, entity_type)
    specs = frameworks_for_question_type(question_type)
    scores = [
        _base_score(
            s,
            question_type=str(question_type or "").lower(),
            entity_type=str(entity_type or "Company"),
            sector=sector,
        )
        for s in specs
    ]
    scores.sort(key=lambda s: -s.score)
    return {
        "applicability_version": APPLICABILITY_VERSION,
        "question_type": question_type,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "sector": sector,
        "scores": [s.to_dict() for s in scores],
        "applicable": [s.to_dict() for s in scores if s.applicable],
        "rejected": [s.to_dict() for s in scores if not s.applicable],
    }


def explain_dcf_for_entity(entity_id: str, entity_type: str | None = None) -> dict[str, Any]:
    """Acceptance helper: Should DCF be used for X?"""
    sector = infer_sector(entity_id, entity_type)
    spec = get_framework("dcf_applicability")
    assert spec is not None
    scored = _base_score(
        spec,
        question_type="valuation",
        entity_type=str(entity_type or "Company"),
        sector=sector,
    )
    return {
        "entity_id": str(entity_id).upper(),
        "sector": sector,
        "applicability": "No" if not scored.applicable else "Yes",
        "score": scored.score,
        "reason": scored.reasons[0] if scored.reasons else "",
        "alternative": (scored.alternatives or ["rel_val_damodaran"])[0],
        "alternatives": scored.alternatives,
    }
