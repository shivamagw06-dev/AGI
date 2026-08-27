"""Apply Research Workflow Framework v1.0."""

from __future__ import annotations

from typing import Any

from research_workflow_framework.next_question import next_best_research_question
from research_workflow_framework.objectives import resolve_decision_objective
from research_workflow_framework.registry import resolve_workflow_for_objective
from research_workflow_framework.schema import FRAMEWORK_VERSION, PROGRAMME, REASONING_PIPELINE
from research_workflow_framework.session import merge_research_session
from research_workflow_framework.status import build_research_status
from research_workflow_framework.validation import validate_workflow_response


def apply_research_workflow_framework(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Orchestrate institutional research workflow above playbooks."""
    if not isinstance(out, dict):
        return out

    query = str(kwargs.get("query") or out.get("query") or "")
    ticker = kwargs.get("ticker") or out.get("ticker")
    company = kwargs.get("company") or out.get("company")
    prior_session = kwargs.get("research_session_state")

    aic = out.get("ask_intelligence_constitution") if isinstance(out.get("ask_intelligence_constitution"), dict) else {}
    aic_intent = aic.get("intent") if isinstance(aic.get("intent"), dict) else None
    irl = kwargs.get("intent_resolution") or out.get("intent_resolution") or {}
    irl_intent = irl.get("intent") if isinstance(irl, dict) else None

    brief = out.get("research_brief") if isinstance(out.get("research_brief"), dict) else {}
    brief_required = brief.get("required_information") or []

    ipf = out.get("institutional_playbook_framework") if isinstance(out.get("institutional_playbook_framework"), dict) else {}
    playbook_resolution = ipf.get("playbook") if isinstance(ipf.get("playbook"), dict) else {}
    playbook_key = playbook_resolution.get("playbook_key")
    journey_state = ipf.get("research_journey_state") if isinstance(ipf.get("research_journey_state"), dict) else {}
    completed_labels = list(journey_state.get("completed_steps") or [])

    objective_pack = resolve_decision_objective(query, irl_intent=irl_intent, aic_intent=aic_intent)
    objective = objective_pack.get("objective") or "Understand Company"
    workflow = resolve_workflow_for_objective(objective)
    workflow_key = workflow.get("workflow_key") or "company_deep_dive"

    evidence_gaps: list[str] = []
    if isinstance(out.get("playbook_validation"), dict) and not out["playbook_validation"].get("passed"):
        evidence_gaps.append("Playbook acceptance tests incomplete")
    if isinstance(out.get("recommendation_status"), dict) and out["recommendation_status"].get("blocked"):
        evidence_gaps.append("Evidence gate blocked pending fuller coverage")

    needs_review: list[str] = []
    rc = out.get("response_constitution") if isinstance(out.get("response_constitution"), dict) else {}
    conf = (rc.get("confidence") or {}).get("score")
    if conf is not None and float(conf) < 50 and "Valuation" in completed_labels:
        needs_review.append("Valuation")

    research_status = build_research_status(
        workflow,
        completed_labels=completed_labels,
        needs_review_labels=needs_review,
        evidence_gaps=evidence_gaps,
    )

    nbrq = next_best_research_question(
        workflow=workflow,
        research_status=research_status,
        ticker=ticker,
        company=company,
    )

    session = merge_research_session(
        prior_session if isinstance(prior_session, dict) else None,
        objective=objective,
        workflow_key=workflow_key,
        ticker=ticker,
        company=company,
        question=query,
        playbook_key=playbook_key,
        completed_labels=completed_labels,
        outstanding_questions=[nbrq.get("question")] if nbrq.get("question") else None,
        current_thesis=str(out.get("thesis") or rc.get("direct_answer") or "")[:500] or None,
    )
    session["research_status"] = research_status.get("overall_status")
    from datetime import UTC, datetime

    session["session_timestamp"] = session.get("session_timestamp") or datetime.now(UTC).isoformat().replace("+00:00", "Z")

    result = {
        "enabled": True,
        "version": FRAMEWORK_VERSION,
        "programme": PROGRAMME,
        "decision_objective": objective_pack,
        "workflow": {
            "workflow_key": workflow_key,
            "name": workflow.get("name"),
            "decision_objective": workflow.get("decision_objective"),
            "playbooks": workflow.get("playbooks"),
        },
        "reasoning_pipeline": list(REASONING_PIPELINE),
        "research_status": research_status,
        "research_session": session,
        "next_best_research_question": nbrq,
        "research_brief_required_information": brief_required,
        "research_brief_top_questions": list(brief.get("top_research_questions") or []),
        "deterministic": True,
        "llm": False,
        "executed_by_investment_os": False,
    }

    out["research_workflow_framework"] = result
    out["decision_objective"] = objective
    out["research_status"] = research_status
    out["research_session"] = session
    out["research_session_state"] = session
    out["next_best_research_question"] = nbrq

    # Prefer workflow next question over generic follow-ups
    if nbrq.get("question"):
        out["suggested_next_research"] = [nbrq["question"]] + [
            x for x in (out.get("suggested_next_research") or []) if x != nbrq["question"]
        ][:5]

    out["workflow_validation"] = validate_workflow_response(out, workflow=workflow, workflow_result=result)
    return out


def health() -> dict[str, Any]:
    from research_workflow_framework.objectives import DECISION_OBJECTIVES
    from research_workflow_framework.registry import WORKFLOW_REGISTRY

    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": FRAMEWORK_VERSION,
        "workflow_count": len(WORKFLOW_REGISTRY),
        "objective_count": len(DECISION_OBJECTIVES),
        "deterministic": True,
        "llm": False,
    }
