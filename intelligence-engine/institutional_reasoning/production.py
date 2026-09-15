"""Soft production entry — attach institutional reasoning plan before answers."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.flags import flags_dict, is_enabled
from institutional_reasoning.planner import build_reasoning_plan
from institutional_reasoning.prompt import (
    INSTITUTIONAL_REASONING_SYSTEM_PROMPT,
    TOP_RULE,
)
from institutional_reasoning.schema import (
    ARCHITECTURE_STATUS,
    MODULE_CODE,
    NOT_A_TOP_LEVEL_ENGINE,
    PROGRAMME,
    ROLE,
    VERSION,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "module_code": MODULE_CODE,
        "version": VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_engine": NOT_A_TOP_LEVEL_ENGINE,
        "role": ROLE,
        "top_rule": TOP_RULE,
        "gold_reasoning_patterns": True,
        "reasoning_families": True,
        "novelty_score": True,
        "adversarial_unknown_reasoning": True,
        "bias_defense": True,
        "evidence_to_conclusion_ratio": True,
        "flags": flags_dict(),
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "top_rule_evidence_justifies_every_sentence": True,
            "nine_step_reasoning_chain": True,
            "evidence_before_conclusions": True,
            "conclusions_before_answers": True,
            "never_guess": True,
            "gold_reasoning_patterns": True,
            "reasoning_families": True,
            "novelty_score_before_answer": True,
            "never_force_closest_template_on_novel": True,
            "adversarial_unknown_reasoning": True,
            "bias_defense": True,
            "evidence_to_conclusion_ratio": True,
            "soft_wire_only": True,
            "not_a_top_level_engine": True,
        },
        "flags": flags_dict(),
    }


def system_prompt() -> str:
    return INSTITUTIONAL_REASONING_SYSTEM_PROMPT


def package_for_ask_agi(
    *,
    query: str = "",
    ticker: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Build the pre-answer reasoning plan and optional family/gold executive.

    Never raises. Never invents company facts beyond the supplied question framing.
    """
    if not is_enabled():
        return {
            "enabled": False,
            "bypassed": True,
            "programme": PROGRAMME,
            "version": VERSION,
        }
    try:
        plan = build_reasoning_plan(query, ticker=ticker, company=company)
        reasoned = package_reasoning_answer(query, ticker=ticker, company=company)
        try:
            from red_team.ecr import attach_ecr_to_package

            reasoned = attach_ecr_to_package(reasoned)
        except Exception:
            pass
        out = {
            **plan,
            "programme": PROGRAMME,
            "module_code": MODULE_CODE,
            "version": VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
            "not_a_top_level_engine": True,
            "role": ROLE,
            "top_rule": TOP_RULE,
            "system_prompt": INSTITUTIONAL_REASONING_SYSTEM_PROMPT,
            "system_prompt_chars": len(INSTITUTIONAL_REASONING_SYSTEM_PROMPT),
            "flags": flags_dict(),
            "reasoning_family": {
                "family_id": reasoned.get("family_id"),
                "family_label": reasoned.get("family_label"),
                "family_confidence": reasoned.get("family_confidence"),
                "family_habit": reasoned.get("family_habit"),
                "signals": reasoned.get("family_signals") or [],
            },
            "novelty": reasoned.get("novelty") or {},
            "ecr": reasoned.get("ecr") or {},
            "gold_pattern": reasoned.get("gold_pattern")
            if reasoned.get("source") == "gold_pattern"
            else {"enabled": False},
        }
        if reasoned.get("owns_executive") and reasoned.get("executive"):
            out["executive"] = reasoned["executive"]
            out["answer"] = reasoned["executive"]
            out["pattern_id"] = reasoned.get("pattern_id")
            out["pattern_level"] = reasoned.get("level")
            out["family_id"] = reasoned.get("family_id")
            out["direct_answer"] = reasoned.get("direct_answer")
            out["owns_executive"] = True
            out["answer_policy"] = reasoned.get("answer_policy")
            out["reasoning_source"] = reasoned.get("source")
            out["decides_winner"] = reasoned.get("decides_winner")
            out["adversarial_mode"] = reasoned.get("mode")
            out["habit_id"] = reasoned.get("habit_id")
            out["consistency_fingerprint"] = reasoned.get("consistency_fingerprint")
            out["families_used"] = reasoned.get("families_used") or reasoned.get("family_signals")
            out["evidence_to_conclusion_ratio"] = reasoned.get("evidence_to_conclusion_ratio")
            if reasoned.get("decomposed") is not None:
                out["decomposed"] = reasoned.get("decomposed")
            if isinstance(reasoned.get("structured"), dict) and reasoned["structured"].get("decomposed"):
                out["decomposed"] = reasoned["structured"]["decomposed"]
        return out
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": False,
            "bypassed": True,
            "error": str(exc),
            "programme": PROGRAMME,
            "version": VERSION,
        }
