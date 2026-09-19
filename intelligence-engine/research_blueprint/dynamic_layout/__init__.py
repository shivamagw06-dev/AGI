"""Dynamic layout — section order changes by report type."""

from __future__ import annotations

import time
from typing import Any

from research_blueprint.assignment_book import build_assignment_book
from research_blueprint.blueprint_registry import get_blueprint
from research_blueprint.ownership_engine import assign_owners
from research_blueprint.quality_rules import build_quality_rules
from research_blueprint.rendering_contract import build_rendering_contract
from research_blueprint.report_policy import build_report_policy
from research_blueprint.report_selector import select_report_type
from research_blueprint.schema import DRBE_VERSION, MANDATORY_OUTPUT_FIELDS, constitution_dict
from research_blueprint.section_generator import SECTION_LABELS, generate_sections
from research_blueprint.section_priority import prioritise_sections

# Canonical order overrides for specific report families
ORDER_OVERRIDES: dict[str, list[str]] = {
    "macro_intelligence_report": [
        "executive_summary",
        "macro_drivers",
        "policy",
        "transmission",
        "forecast",
        "risks",
        "conclusion",
    ],
}


def _ordered(keys: list[str], report_type: str, preferred: list[str]) -> list[str]:
    override = ORDER_OVERRIDES.get(report_type)
    if override:
        base = [k for k in override if k in keys]
        rest = [k for k in keys if k not in base]
        return base + rest
    # Prefer registry mandatory order then optional
    base = [k for k in preferred if k in keys]
    rest = [k for k in keys if k not in base]
    return base + rest


def build_research_blueprint(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = body or {}
    primary_objective = (
        payload.get("primary_objective")
        or payload.get("objective")
        or (payload.get("research_objective") or {}).get("primary_objective")
    )
    intent_family = payload.get("intent_family") or payload.get("family")
    required_analysts = list(
        payload.get("required_analysts")
        or (payload.get("analyst_router") or {}).get("required_analysts")
        or []
    )

    selected = select_report_type(
        question=question,
        primary_objective=str(primary_objective) if primary_objective else None,
        intent_family=str(intent_family) if intent_family else None,
    )
    report_type = selected["report_type"]
    generated = generate_sections(report_type)
    bp_meta = get_blueprint(report_type) or {}

    priorities = prioritise_sections(
        report_type=report_type,
        mandatory=generated["mandatory"],
        optional=generated["optional"],
        suppress_default=generated["suppress_default"],
        primary_objective=str(primary_objective) if primary_objective else None,
        intent_family=str(intent_family) if intent_family else None,
    )

    active_keys = (
        list(priorities["mandatory_sections"])
        + list(priorities["optional_sections"])
        + list(priorities["hidden_sections"])
    )
    preferred_order = list(generated["mandatory"]) + list(generated["optional"])
    section_order = _ordered(active_keys, report_type, preferred_order)

    ownership = assign_owners(section_keys=section_order, required_analysts=required_analysts)
    quality = build_quality_rules(report_type, bp_meta)
    policy = build_report_policy(report_type, bp_meta, priorities)
    rendering = build_rendering_contract(
        section_order=section_order,
        section_owner=ownership["section_owner"],
        priorities=priorities["priorities"],
        quality_rules=quality,
    )
    assignments = build_assignment_book(
        question=question,
        report_type=report_type,
        section_order=section_order,
        section_owner=ownership["section_owner"],
        priorities=priorities["priorities"],
    )

    sections = [
        {
            "section_key": key,
            "label": SECTION_LABELS.get(key, key.replace("_", " ").title()),
            "owner": ownership["section_owner"].get(key),
            "priority": priorities["priorities"].get(key, "optional"),
            "order": i + 1,
        }
        for i, key in enumerate(section_order)
    ]

    # Visual ownership chain (unique owners in section order)
    visual = []
    seen_owners: set[str] = set()
    for key in section_order:
        owner = ownership["section_owner"].get(key)
        if owner and owner not in seen_owners and priorities["priorities"].get(key) != "hidden":
            seen_owners.add(owner)
            visual.append({"owner": owner, "via_section": key})

    planning_ms = (time.perf_counter() - t0) * 1000.0
    out = {
        "ok": True,
        "question": question,
        "report_type": report_type,
        "report_name": generated.get("report_name") or bp_meta.get("report_name"),
        "purpose": generated.get("purpose"),
        "audience": generated.get("audience"),
        "selection_reason": selected.get("selection_reason"),
        "primary_objective": selected.get("primary_objective") or primary_objective,
        "intent_family": selected.get("intent_family") or intent_family,
        "sections": sections,
        "section_order": section_order,
        "section_owner": ownership["section_owner"],
        "hidden_sections": priorities["hidden_sections"],
        "optional_sections": priorities["optional_sections"],
        "mandatory_sections": priorities["mandatory_sections"],
        "suppressed_sections": priorities["suppressed_sections"],
        "quality_rules": quality,
        "rendering_contract": rendering,
        "report_policy": policy,
        "assignment_book": assignments,
        "visual_view": visual,
        "metrics": {
            "blueprint_ms": round(planning_ms, 4),
            "section_count": len(section_order),
            "mandatory_count": len(priorities["mandatory_sections"]),
            "ownership_complete": ownership["ownership_complete"],
            "no_irrelevant_sections": priorities["no_irrelevant_sections"],
        },
        "drbe_version": DRBE_VERSION,
        "constitution_id": constitution_dict().get("id"),
        "not_a_top_level_intelligence_layer": True,
        "mandatory_fields_present": True,
    }
    # verify mandatory fields
    out["mandatory_fields_present"] = all(f in out for f in MANDATORY_OUTPUT_FIELDS)
    return out
