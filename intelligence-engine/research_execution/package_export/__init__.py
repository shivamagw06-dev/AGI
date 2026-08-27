"""Package export — JSON / Markdown / Audit / Internal."""

from __future__ import annotations

import json
from typing import Any


def export_json(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "json",
        "package_id": package.get("package_id"),
        "body": package,
    }


def export_markdown(package: dict[str, Any]) -> dict[str, Any]:
    q = (package.get("question") or {}).get("original") or ""
    entity = package.get("entity") or {}
    intent = package.get("intent") or {}
    analysts = (package.get("analyst_plan") or {}).get("required_analysts") or []
    layers = (package.get("layer_plan") or {}).get("required_layers") or []
    blueprint = package.get("blueprint") or {}
    validation = package.get("validation") or {}
    contract = package.get("research_contract") or {}
    lines = [
        f"# Institutional Research Execution Package",
        f"",
        f"**Package ID:** {package.get('package_id')}",
        f"**Question:** {q}",
        f"**Entity:** {entity.get('canonical_name') or entity.get('ticker') or '—'}",
        f"**Objective:** {intent.get('research_objective') or intent.get('primary_intent') or '—'}",
        f"**Report:** {blueprint.get('report_name') or blueprint.get('report_type') or '—'}",
        f"**Readiness:** {validation.get('readiness_state') or '—'}",
        f"",
        f"## Analysts",
        ", ".join(analysts) or "—",
        f"",
        f"## Layers",
        ", ".join(layers) or "—",
        f"",
        f"## Research Contract Objective",
        str(contract.get("objective") or "—"),
        f"",
        f"_Immutable planning package — consumers may not alter intent, entity, objective, blueprint, or routing._",
    ]
    return {"format": "markdown", "package_id": package.get("package_id"), "body": "\n".join(lines)}


def export_audit(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "audit",
        "package_id": package.get("package_id"),
        "body": package.get("audit") or {},
    }


def export_internal(package: dict[str, Any]) -> dict[str, Any]:
    """Compact internal handoff for analysts / layers / CIO / writer."""
    return {
        "format": "internal",
        "package_id": package.get("package_id"),
        "body": {
            "package_id": package.get("package_id"),
            "immutable": True,
            "question": package.get("question"),
            "entity": package.get("entity"),
            "intent": package.get("intent"),
            "analyst_plan": package.get("analyst_plan"),
            "layer_plan": package.get("layer_plan"),
            "blueprint": package.get("blueprint"),
            "validation": {
                "readiness_state": (package.get("validation") or {}).get("readiness_state"),
                "execution_allowed": (package.get("validation") or {}).get("execution_allowed"),
                "overall_readiness": (package.get("validation") or {}).get("overall_readiness"),
            },
            "research_contract": package.get("research_contract"),
            "execution_plan": package.get("execution_plan"),
            "quality_targets": package.get("quality_targets"),
        },
    }


def export_package(package: dict[str, Any], fmt: str = "json") -> dict[str, Any]:
    fmt = (fmt or "json").lower()
    if fmt == "markdown":
        return export_markdown(package)
    if fmt == "audit":
        return export_audit(package)
    if fmt == "internal":
        return export_internal(package)
    return export_json(package)


def dumps_json(package: dict[str, Any]) -> str:
    return json.dumps(package, indent=2, default=str)
