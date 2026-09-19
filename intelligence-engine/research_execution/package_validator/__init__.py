"""Package validator — completeness, consistency, no conflicting plans."""

from __future__ import annotations

from typing import Any

from research_execution.schema import MANDATORY_PACKAGE_SECTIONS


def validate_package(package: dict[str, Any]) -> dict[str, Any]:
    missing = [s for s in MANDATORY_PACKAGE_SECTIONS if s not in package or package.get(s) is None]
    conflicts: list[str] = []

    analysts = package.get("analyst_plan") or {}
    layers = package.get("layer_plan") or {}
    req_a = set(analysts.get("required_analysts") or [])
    sup_a = set(analysts.get("suppressed_analysts") or [])
    req_l = set(layers.get("required_layers") or [])
    sup_l = set(layers.get("suppressed_layers") or [])

    if req_a & sup_a:
        conflicts.append("analyst_required_and_suppressed")
    if req_l & sup_l:
        conflicts.append("layer_required_and_suppressed")

    blueprint = package.get("blueprint") or {}
    validation = package.get("validation") or {}
    intent = package.get("intent") or {}

    # Educational blueprint should not require Portfolio/Committee analysts as mandatory owners conflict
    report = str(blueprint.get("report_type") or "")
    if report == "educational_guide" and ("Portfolio" in req_a and "Portfolio" not in (analysts.get("optional_analysts") or [])):
        # soft: only conflict if Portfolio is required AND not suppressed
        if "Portfolio" not in sup_a and "explain" in str((package.get("question") or {}).get("original") or "").lower():
            conflicts.append("educational_portfolio_conflict")

    # Validation blocked but execution plan says go
    if validation.get("readiness_state") == "BLOCKED" and (package.get("execution_plan") or {}).get("may_execute"):
        conflicts.append("blocked_but_executable")

    # Intent vs blueprint coarse consistency
    primary = str(intent.get("primary_intent") or intent.get("research_objective") or "").lower()
    if "educational" in primary and report and report not in {"educational_guide", ""}:
        conflicts.append("intent_blueprint_mismatch")
    if ("peer comparison" in primary or "comparison" in primary) and report and report not in {
        "comparison_report",
        "",
    }:
        # allow empty inferred
        if report not in {"comparison_report"}:
            conflicts.append("intent_blueprint_mismatch")

    contract = package.get("research_contract") or {}
    if not contract.get("objective"):
        missing.append("research_contract.objective")

    complete = len(missing) == 0
    consistent = len(conflicts) == 0
    return {
        "package_complete": complete,
        "package_consistent": consistent,
        "missing_sections": missing,
        "conflicts": conflicts,
        "no_conflicting_plans": consistent,
        "score": 1.0 if complete and consistent else (0.7 if complete else 0.4),
    }
