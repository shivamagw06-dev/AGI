"""IKI production facade."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.applicability import explain_dcf_for_entity, score_applicability
from institutional_reasoning.iki.compiler_v2 import compile_library
from institutional_reasoning.iki.confidence import all_profiles
from institutional_reasoning.iki.judgement_suite import run_judgement_suite
from institutional_reasoning.iki.planner import plan
from institutional_reasoning.iki.registry import registry_snapshot
from institutional_reasoning.iki.schema import IKI_VERSION, MODULE_CODE, PROGRAMME


def package_for_governance(
    *,
    question: str,
    question_type: str,
    entity: dict[str, Any] | None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return plan(
        question=question,
        question_type=question_type,
        entity=entity,
        evidence=evidence,
    )


def dashboard() -> dict[str, Any]:
    reg = registry_snapshot()
    ijs = run_judgement_suite()
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IKI_VERSION,
        "registry_n": reg.get("n"),
        "confidence_profiles": all_profiles(),
        "compiler": compile_library(),
        "judgement_suite": {
            "score": ijs.get("score"),
            "passed": ijs.get("phase3_gate", {}).get("passed"),
            "n": ijs.get("n"),
        },
        "sample_dcf_bank": explain_dcf_for_entity("HDFCBANK"),
        "sample_applicability_zomato": score_applicability(
            question_type="valuation",
            entity_id="ZOMATO",
            entity_type="Company",
        ),
    }


def quality_gates() -> dict[str, Any]:
    ijs = run_judgement_suite()
    reg = registry_snapshot()
    return {
        "gate": "INSTITUTIONAL_KNOWLEDGE_INTELLIGENCE",
        "version": IKI_VERSION,
        "registry_ok": int(reg.get("n") or 0) >= 8,
        "judgement_score": ijs.get("score"),
        "passed": bool((ijs.get("phase3_gate") or {}).get("passed")) and int(reg.get("n") or 0) >= 8,
        "phase3_gate": ijs.get("phase3_gate"),
        "failures": [r for r in (ijs.get("results") or []) if not r.get("passed")],
    }
