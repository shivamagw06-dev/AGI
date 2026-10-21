"""Module 1 — Learning Candidate Generator.

Every reviewed decision asks: should anything change?
Never: "Rewrite framework."
"""

from __future__ import annotations

import uuid
from typing import Any

from institutional_reasoning.cal.regime import detect_regime
from institutional_reasoning.cal.schema import CAL_VERSION

CANDIDATE_VERSION = "learning-candidate-v1.0.0"


def generate_candidates(outcome_record: dict[str, Any]) -> dict[str, Any]:
    """Produce governed learning candidates from an IOI review record."""
    attribution = outcome_record.get("attribution") or {}
    evaluation = outcome_record.get("evaluation") or {}
    review = outcome_record.get("review") or {}
    calibration = outcome_record.get("calibration") or {}
    lifecycle = outcome_record.get("lifecycle") or {}
    market = outcome_record.get("market") or {}

    if outcome_record.get("status") == "withheld" or lifecycle.get("withheld"):
        return {
            "candidate_version": CANDIDATE_VERSION,
            "cal_version": CAL_VERSION,
            "decision_id": outcome_record.get("decision_id") or lifecycle.get("decision_id"),
            "candidates": [
                {
                    "proposal_id": f"lp_{uuid.uuid4().hex[:12]}",
                    "kind": "no_change",
                    "reason": "Withheld decision — no behavioural learning candidate",
                    "auto_apply": False,
                }
            ],
            "regime": detect_regime(market=market),
        }

    wrong = list(attribution.get("wrong") or [])
    primary = attribution.get("primary_failure") or {}
    score = float(evaluation.get("score") or 0.0)
    regime = detect_regime(
        market=market,
        hint=(market.get("scenario_realised") if market.get("scenario_realised") in {"bull", "bear"} else None),
    )
    candidates: list[dict[str, Any]] = []

    def _add(kind: str, **payload: Any) -> None:
        candidates.append(
            {
                "proposal_id": f"lp_{uuid.uuid4().hex[:12]}",
                "kind": kind,
                "auto_apply": False,
                "regime": regime.get("regime"),
                "decision_id": outcome_record.get("decision_id") or lifecycle.get("decision_id"),
                "djg": lifecycle.get("research_djg"),
                "pdg": lifecycle.get("portfolio_djg"),
                "og_ref": outcome_record.get("decision_id"),
                **payload,
            }
        )

    # Confidence adjustments from calibration rows
    for fw in calibration.get("frameworks") or []:
        ies = float(fw.get("ies_confidence") or 0.9)
        live = float(fw.get("live_outcome_confidence") or ies)
        fid = str(fw.get("framework") or "")
        if live + 0.05 < ies and fw.get("last_verdict") == "Wrong":
            _add(
                "decrease_confidence",
                target=fid,
                from_value=ies,
                to_value=round(max(0.5, live), 4),
                reason=f"Live outcome confidence below IES for {fid}",
            )
        elif live > ies + 0.03 and fw.get("last_verdict") == "Correct":
            _add(
                "increase_confidence",
                target=fid,
                from_value=ies,
                to_value=round(min(0.99, (ies + live) / 2), 4),
                reason=f"Live outcomes support higher confidence for {fid}",
            )

    # Planner priority from primary failure
    if primary.get("kind") in {"macro", "scenario", "valuation", "business_quality"} or primary.get("component"):
        target = str(primary.get("component") or primary.get("kind"))
        if target in {"macro", "scenario", "policy", "sizing", "evidence", "assumption"}:
            if target == "macro":
                _add(
                    "add_failure_condition",
                    target="macro",
                    condition="sector_stress_with_positive_thesis",
                    reason="Macro attribution failed under adverse sector path",
                )
            elif target == "sizing":
                _add(
                    "adjust_policy",
                    target="max_stock_weight",
                    from_value=0.08,
                    to_value=0.06,
                    reason="Repeated sizing stress — propose lower max weight (human approval)",
                )
            elif target == "scenario":
                _add(
                    "add_failure_condition",
                    target="scenario",
                    condition="bear_realised_underweighted",
                    reason="Scenario accuracy weak when bear realised",
                )
        else:
            _add(
                "adjust_planner_priority",
                target=target,
                delta=-0.04,
                reason=f"Primary failure attributed to {target} — small priority reduction",
            )

    # Applicability learning for repeated wrong frameworks
    for w in wrong:
        if any(x in str(w) for x in ("dcf", "rel_val", "hist_multiples", "business_quality")):
            _add(
                "add_applicability_rule",
                target=str(w),
                rule="reduce_applicability",
                scope={"regime": regime.get("regime"), "ticker": lifecycle.get("ticker")},
                reason=f"Framework {w} marked Wrong in outcome review",
            )

    # Policy learning when portfolio quality poor
    pq = float(((review.get("portfolio_quality") or {}).get("score") or 100))
    if pq < 55 or "policy" in wrong or "sizing" in wrong:
        _add(
            "adjust_policy",
            target="max_stock_weight",
            from_value=0.08,
            to_value=0.06,
            reason="Portfolio quality weak — consider tighter single-name limit",
            requires_human_approval=True,
        )

    if score >= 85 and not wrong:
        _add("no_change", reason="High-quality outcome — no behavioural change proposed")

    if not candidates:
        _add("no_change", reason="No actionable learning signal")

    # Hard rule: never rewrite framework
    for c in candidates:
        c["forbidden"] = ["rewrite_framework", "silent_self_modification", "auto_deploy_without_simulation"]
        c["requires_governance"] = True

    return {
        "candidate_version": CANDIDATE_VERSION,
        "cal_version": CAL_VERSION,
        "decision_id": outcome_record.get("decision_id") or lifecycle.get("decision_id"),
        "regime": regime,
        "candidates": candidates,
        "count": len(candidates),
    }
