"""Apply Ask Intelligence Constitution v1.0 to an answer pack."""

from __future__ import annotations

from typing import Any

from ask_intelligence_constitution.assembler import assemble_sections, institutional_thinking_framework
from ask_intelligence_constitution.intent import resolve_investment_intent
from ask_intelligence_constitution.schema import CONFIDENCE_METHODOLOGY, CONSTITUTION_VERSION, PROGRAMME
from ask_intelligence_constitution.validation import validate_ask_response


def apply_ask_intelligence_constitution(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Enforce institutional response methodology on every Ask answer."""
    if not isinstance(out, dict):
        return out

    query = str(kwargs.get("query") or out.get("query") or "")
    irl = kwargs.get("intent_resolution") or out.get("intent_resolution") or {}
    irl_intent = irl.get("intent") or irl.get("primary_intent")

    intent = resolve_investment_intent(query, irl_intent=irl_intent)
    rc = out.get("response_constitution") if isinstance(out.get("response_constitution"), dict) else {}

    gaps: list[str] = []
    ia = out.get("institutional_answer") if isinstance(out.get("institutional_answer"), dict) else {}
    if ia.get("evidence_insufficient"):
        gaps.append("Validated financial and valuation evidence incomplete")
    if isinstance(out.get("recommendation_status"), dict) and out["recommendation_status"].get("blocked"):
        gaps.append("Recommendation gate blocked pending fuller evidence")

    sections = assemble_sections(out, intent=intent, response_constitution=rc)
    thinking = institutional_thinking_framework(intent, gaps=gaps)

    constitution = {
        "enabled": True,
        "version": CONSTITUTION_VERSION,
        "programme": PROGRAMME,
        "intent": intent,
        "sections": sections,
        "section_order": list(sections.keys()),
        "institutional_thinking_framework": thinking,
        "confidence_methodology": CONFIDENCE_METHODOLOGY,
        "forbidden": "BUY, SELL, HOLD, target price, entry/exit — research conclusion only",
        "user_decides": True,
    }

    out["ask_intelligence_constitution"] = constitution
    out["answer_structure"] = "ask_intelligence_constitution_v1"
    out["research_conclusion"] = sections.get("research_conclusion")
    out["questions_before_you_decide"] = sections.get("questions_before_you_decide")

    # Sanitize house_label if it looks like trading advice
    label = out.get("house_label") or kwargs.get("house_label")
    if label and str(label).strip().lower() in {"buy", "sell", "strong buy", "strong sell"}:
        out["house_label"] = "Research Priority"

    out["ask_constitution_validation"] = validate_ask_response(out)
    return out


def health() -> dict[str, Any]:
    from ask_intelligence_constitution.schema import OUTPUT_SECTIONS, PRIMARY_INTENTS

    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": CONSTITUTION_VERSION,
        "primary_intents": list(PRIMARY_INTENTS),
        "output_sections": list(OUTPUT_SECTIONS),
        "deterministic": True,
        "llm": False,
    }
