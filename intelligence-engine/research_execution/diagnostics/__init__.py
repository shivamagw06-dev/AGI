"""IREP diagnostics — explain package composition and consistency."""

from __future__ import annotations

from typing import Any

from research_execution.package_builder import build_execution_package


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    pkg = build_execution_package(question, body)
    return {
        "package_id": pkg.get("package_id"),
        "question": (pkg.get("question") or {}).get("original"),
        "entity": pkg.get("entity"),
        "intent": pkg.get("intent"),
        "analyst_plan": {
            "required": (pkg.get("analyst_plan") or {}).get("required_analysts"),
            "suppressed": (pkg.get("analyst_plan") or {}).get("suppressed_analysts"),
        },
        "layer_plan": {
            "required": (pkg.get("layer_plan") or {}).get("required_layers"),
            "suppressed": (pkg.get("layer_plan") or {}).get("suppressed_layers"),
        },
        "blueprint": {
            "report_type": (pkg.get("blueprint") or {}).get("report_type"),
            "section_order": (pkg.get("blueprint") or {}).get("section_order"),
        },
        "api_plan": pkg.get("api_plan"),
        "validation": pkg.get("validation"),
        "research_contract": {
            "objective": (pkg.get("research_contract") or {}).get("objective"),
            "minimum_evidence": (pkg.get("research_contract") or {}).get("minimum_evidence"),
            "must_not": (pkg.get("research_contract") or {}).get("must_not"),
        },
        "package_complete": pkg.get("package_complete"),
        "package_consistent": pkg.get("package_consistent"),
        "validation_detail": pkg.get("validation_detail"),
        "audit": pkg.get("audit"),
        "metrics": pkg.get("metrics"),
    }
