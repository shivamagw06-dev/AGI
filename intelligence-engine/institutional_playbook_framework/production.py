"""Apply Institutional Playbook Framework v1.0 to an answer pack."""

from __future__ import annotations

from typing import Any

from institutional_playbook_framework.journey import build_journey_map, suggest_next_research
from institutional_playbook_framework.memory import merge_journey_state
from institutional_playbook_framework.registry import get_playbook
from institutional_playbook_framework.resolver import resolve_playbook
from institutional_playbook_framework.schema import (
    EXECUTION_PIPELINE,
    FRAMEWORK_VERSION,
    OUTPUT_PRINCIPLES,
    PROGRAMME,
    REASONING_RULES,
    USER_GUIDANCE_QUESTIONS,
)
from institutional_playbook_framework.validation import validate_playbook_response


def _build_sections(pack: dict[str, Any], playbook: dict[str, Any]) -> dict[str, Any]:
    rc = pack.get("response_constitution") if isinstance(pack.get("response_constitution"), dict) else {}
    thesis = rc.get("investment_thesis") if isinstance(rc.get("investment_thesis"), dict) else {}
    return {
        "executive_summary": rc.get("direct_answer") or pack.get("executive"),
        "business_quality": thesis.get("business"),
        "financial_strength": thesis.get("financial_quality"),
        "growth_outlook": thesis.get("growth"),
        "valuation": thesis.get("valuation"),
        "risks": thesis.get("risks"),
        "catalysts": thesis.get("catalysts"),
        "research_conclusion": pack.get("research_conclusion"),
        "questions_before_you_decide": pack.get("questions_before_you_decide"),
    }


def apply_institutional_playbook_framework(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Enforce playbook methodology on every Ask answer."""
    if not isinstance(out, dict):
        return out

    query = str(kwargs.get("query") or out.get("query") or "")
    irl = kwargs.get("intent_resolution") or out.get("intent_resolution") or {}
    irl_intent = irl.get("intent") if isinstance(irl, dict) else None
    iap_sel = kwargs.get("playbook_selection") or out.get("playbook_selection") or {}
    ticker = kwargs.get("ticker") or out.get("ticker")
    prior_journey = kwargs.get("research_journey_state")

    resolution = resolve_playbook(query, irl_intent=irl_intent, playbook_selection=iap_sel)
    playbook_key = resolution.get("playbook_key") or "investment_assessment"
    playbook = get_playbook(playbook_key) or get_playbook("investment_assessment") or {}

    sections = _build_sections(out, playbook)
    journey_steps = list(resolution.get("journey_steps") or playbook.get("journey_steps") or [])

    journey_state = merge_journey_state(
        prior_journey if isinstance(prior_journey, dict) else None,
        ticker=ticker,
        playbook_key=playbook_key,
        journey_steps=journey_steps,
        question=query,
        playbook_selection=iap_sel if isinstance(iap_sel, dict) else None,
        response_sections=sections,
    )
    journey_map = build_journey_map(
        journey_steps=journey_steps,
        completed_steps=journey_state.get("completed_steps") or [],
        ticker=ticker,
    )
    next_research = suggest_next_research(journey_map=journey_map, playbook=playbook, ticker=ticker)

    framework = {
        "enabled": True,
        "version": FRAMEWORK_VERSION,
        "programme": PROGRAMME,
        "playbook": resolution,
        "execution_pipeline": list(EXECUTION_PIPELINE),
        "reasoning_rules": list(REASONING_RULES),
        "output_principles": list(OUTPUT_PRINCIPLES),
        "sections": sections,
        "research_journey": journey_map,
        "research_journey_state": journey_state,
        "suggested_next_research": next_research,
        "user_guidance_questions": list(USER_GUIDANCE_QUESTIONS),
        "deterministic": True,
        "llm": False,
        "consumes_investment_os": True,
    }

    out["institutional_playbook_framework"] = framework
    out["research_journey"] = journey_map
    out["research_journey_state"] = journey_state
    out["suggested_next_research"] = next_research

    if not out.get("questions_before_you_decide"):
        out["questions_before_you_decide"] = list(USER_GUIDANCE_QUESTIONS)[:6]

    out["playbook_validation"] = validate_playbook_response(out, playbook=playbook)
    return out


def health() -> dict[str, Any]:
    from institutional_playbook_framework.registry import list_playbook_keys, registry_summary

    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": FRAMEWORK_VERSION,
        "playbook_count": len(list_playbook_keys()),
        "registry": registry_summary(),
        "deterministic": True,
        "llm": False,
    }
