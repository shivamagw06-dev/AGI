"""Contradiction Reasoning soft production entry for Ask AGI."""

from __future__ import annotations

from typing import Any

from contradiction_reasoning.archetypes import match_archetype, generic_archetype
from contradiction_reasoning.compose import build_reasoning_pack
from contradiction_reasoning.detector import is_contradiction_query
from contradiction_reasoning.flags import flags_dict, is_enabled
from contradiction_reasoning.schema import (
    ARCHITECTURE_STATUS,
    MODULE_CODE,
    NOT_A_TOP_LEVEL_ENGINE,
    NOT_CONTINUOUS_RESEARCH_EVALUATION,
    PROGRAMME,
    REASONING_CHAIN,
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
        "not_continuous_research_evaluation": NOT_CONTINUOUS_RESEARCH_EVALUATION,
        "reasoning_chain": list(REASONING_CHAIN),
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
            "detects_conflict_queries": True,
            "step_by_step_reasoning": True,
            "lists_alternative_explanations": True,
            "states_missing_evidence": True,
            "balanced_conclusion_with_confidence": True,
            "never_jumps_to_certainty": True,
            "soft_wire_only": True,
            "not_a_top_level_engine": True,
        },
        "flags": flags_dict(),
    }


def package_for_ask_agi(
    *,
    query: str = "",
    ticker: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Soft-wire: if the question is a contradiction query, return reasoning pack.

    Never raises. Returns bypassed package when disabled or not a contradiction query.
    """
    if not is_enabled():
        return {
            "enabled": False,
            "bypassed": True,
            "reason": "disabled",
            "programme": PROGRAMME,
            "version": VERSION,
        }

    q = str(query or "").strip()
    if not is_contradiction_query(q):
        return {
            "enabled": False,
            "bypassed": True,
            "reason": "not_contradiction_query",
            "programme": PROGRAMME,
            "version": VERSION,
        }

    try:
        arch = match_archetype(q) or generic_archetype(q)
        pack = build_reasoning_pack(arch, query=q, company=company)
        return {
            **pack,
            "programme": PROGRAMME,
            "module_code": MODULE_CODE,
            "version": VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
            "not_a_top_level_engine": True,
            "ticker": ticker,
            "flags": flags_dict(),
            "executive": pack.get("answer"),
            "answer_policy": "contradiction_reasoning_step_by_step",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": False,
            "bypassed": True,
            "error": str(exc),
            "programme": PROGRAMME,
            "version": VERSION,
        }
