"""IOI pipeline — register decisions and evaluate outcomes (no learning)."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ioi.attribution import attribute_outcome
from institutional_reasoning.ioi.calibration import calibrate_frameworks
from institutional_reasoning.ioi.evaluator import evaluate_prediction
from institutional_reasoning.ioi.lifecycle import get_decision, register_decision, update_decision
from institutional_reasoning.ioi.market import collect_outcome
from institutional_reasoning.ioi.memory import remember_outcome
from institutional_reasoning.ioi.outcome_graph import build_outcome_graph
from institutional_reasoning.ioi.review import convene_review
from institutional_reasoning.ioi.schema import IOI_VERSION, MODULE_CODE, PROGRAMME
from institutional_reasoning.ioi.scoreboard import build_scoreboard, note_failure_mode

PIPELINE_VERSION = "outcome-pipeline-v1.0.0"


def track_decision(
    ipi_decision: dict[str, Any],
    *,
    research_record: dict[str, Any] | None = None,
    benchmark: str = "NIFTY50",
) -> dict[str, Any]:
    """Soft-wire entry: IPI decision → lifecycle object."""
    if not ipi_decision:
        return {"found": False, "reason": "no_ipi_decision"}
    life = register_decision(ipi_decision, research_record=research_record, benchmark=benchmark)
    return {
        "found": True,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IOI_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "decision_id": life["decision_id"],
        "lifecycle": life,
        "status": life.get("status"),
    }


def evaluate_decision(
    decision_id: str,
    *,
    market_override: dict[str, Any] | None = None,
    scenario_realised: str | None = None,
    force_wrong: dict[str, bool] | None = None,
    persist: bool = True,
    propose_learning: bool = True,
) -> dict[str, Any]:
    """Full review: market → evaluate → attribute → calibrate → review → OG."""
    life = get_decision(decision_id)
    if not life:
        return {"found": False, "reason": "unknown_decision", "decision_id": decision_id}
    if life.get("withheld") or life.get("status") == "withheld":
        return {
            "found": True,
            "decision_id": decision_id,
            "status": "withheld",
            "note": "Withheld decisions are tracked but not scored against market outcomes.",
            "lifecycle": life,
            "learning_applied": False,
        }

    update_decision(decision_id, status="under_review")
    market = collect_outcome(
        life.get("ticker"),
        override=market_override,
        scenario_realised=scenario_realised,
    )
    evaluation = evaluate_prediction(life, market)
    attribution = attribute_outcome(life, market, evaluation, force_wrong=force_wrong)

    # Failure mode notes for scoreboard (observational)
    for w in attribution.get("wrong") or []:
        note_failure_mode(str(w), f"verdict_wrong:{evaluation.get('grade')}")

    calibration = calibrate_frameworks(attribution)
    review = convene_review(life, evaluation, attribution, market)
    scoreboard = build_scoreboard(calibration)

    record = {
        "found": True,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IOI_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "decision_id": decision_id,
        "lifecycle": life,
        "market": market,
        "evaluation": evaluation,
        "attribution": attribution,
        "calibration": calibration,
        "review": review,
        "scoreboard": scoreboard,
        "learning_applied": False,
    }
    record["outcome_graph"] = build_outcome_graph(record)

    # Phase 7 — Learning Governance: generate proposals only (never auto-deploy here).
    if propose_learning:
        try:
            from institutional_reasoning.cal.governance import propose_from_outcome

            learning = propose_from_outcome(record)
            record["learning_proposals"] = {
                "count": learning.get("count"),
                "regime": learning.get("regime"),
                "proposal_ids": [p.get("proposal_id") for p in (learning.get("proposals") or [])],
                "auto_deployed": False,
                "note": "Proposals require Simulation → Approval → Version before production overlays.",
            }
        except Exception:
            record["learning_proposals"] = {"count": 0, "auto_deployed": False}

    update_decision(
        decision_id,
        status="evaluated",
        evaluation=evaluation,
        attribution=attribution,
        review=review,
        market=market,
        outcome_graph=record["outcome_graph"],
    )
    if persist:
        remember_outcome(record)
    return record
