"""Apply Institutional Writing Constitution v1.1 — IRE communication layer."""

from __future__ import annotations

from typing import Any

from institutional_writing_constitution.assembler import assemble_writing_sections, infer_answer_length
from institutional_writing_constitution.evaluation import (
    evaluation_rubric,
    score_institutional_readability,
    score_writing_pack,
)
from institutional_writing_constitution.response_planner import plan_response
from institutional_writing_constitution.schema import (
    CONSTITUTION_VERSION,
    LAYER,
    LEGACY_SECTION_ALIASES,
    PROGRAMME,
    WRITING_PHILOSOPHY,
)
from institutional_writing_constitution.validation import validate_writing_response


def apply_institutional_writing_constitution(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Research → Response Planning → Writing."""
    if not isinstance(out, dict):
        return out

    query = str(kwargs.get("query") or out.get("query") or "")
    ticker = kwargs.get("ticker") or out.get("ticker")
    company = kwargs.get("company") or out.get("company") or ticker or "This company"

    plan = plan_response(
        out,
        query=query,
        ticker=ticker,
        company=str(company),
        research_brief=out.get("research_brief") if isinstance(out.get("research_brief"), dict) else None,
    )
    sections = assemble_writing_sections(
        out,
        company=str(company),
        ticker=ticker,
        template_id=plan["template_id"],
        section_order=plan["section_order"],
    )
    length_class = plan.get("answer_length_class") or infer_answer_length(query)

    constitution = {
        "enabled": True,
        "version": CONSTITUTION_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "purpose": "Defines how AGI explains — not how AGI thinks",
        "response_plan": plan,
        "template_id": plan["template_id"],
        "template_label": plan["template_label"],
        "sections": sections,
        "section_order": plan["section_order"],
        "writing_philosophy": list(WRITING_PHILOSOPHY),
        "answer_length_class": length_class,
        "primary_objective": "Improve the user's investment understanding",
        "never_recommends": True,
        "user_decides": True,
        "evaluation_rubric": evaluation_rubric(),
        "pipeline": "research → response_planning → writing",
    }

    out["institutional_writing_constitution"] = constitution
    out["writing_structure"] = "institutional_writing_constitution_v1_1"
    out["response_plan"] = plan
    out["writing_sections"] = sections
    out["executive_summary"] = sections.get("executive_summary")
    out["what_matters_most"] = sections.get("what_matters_most")
    out["investment_debate"] = sections.get("investment_debate")
    out["supporting_evidence"] = sections.get("supporting_evidence")
    out["key_uncertainties"] = sections.get("key_uncertainties")

    # Legacy v1.0 aliases for downstream consumers
    for legacy, current in LEGACY_SECTION_ALIASES.items():
        if sections.get(current) is not None:
            out[legacy] = sections[current]

    if sections.get("research_conclusion"):
        out["research_conclusion"] = sections["research_conclusion"]
    qsec = sections.get("questions_before_you_decide") or {}
    if qsec.get("questions"):
        out["questions_before_you_decide"] = qsec["questions"]

    out["writing_constitution_validation"] = validate_writing_response(out)
    out["writing_score"] = score_writing_pack(out)
    out["institutional_readability_score"] = score_institutional_readability(out)
    return out


def health() -> dict[str, Any]:
    from institutional_writing_constitution.evaluation import BENCHMARK_QUESTIONS, TARGET_BENCHMARK_COUNT
    from institutional_writing_constitution.templates import RESPONSE_TEMPLATES

    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": CONSTITUTION_VERSION,
        "layer": LAYER,
        "response_templates": len(RESPONSE_TEMPLATES),
        "pipeline": "research → response_planning → writing",
        "benchmark_questions": len(BENCHMARK_QUESTIONS),
        "benchmark_target": TARGET_BENCHMARK_COUNT,
        "deterministic": True,
        "llm": False,
    }
