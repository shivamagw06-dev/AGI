"""Coverage levels 0–7 for Institutional Company Intelligence."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence.schema import (
    COVERAGE_LEVELS,
    INSTITUTIONAL_COMPLETE_LEVEL,
    coverage_level_name,
)


def _present(modules: dict[str, Any], name: str) -> bool:
    return isinstance(modules.get(name), dict) and bool(modules.get(name))


def compute_coverage_level(modules: dict[str, Any], *, gate_pass: bool = False) -> dict[str, Any]:
    """Assign coverage level from module presence.

    Level 7 requires all modules present AND quality gates pass.
    """
    level = 0
    if _present(modules, "identity"):
        level = 1
    if level >= 1 and _present(modules, "business_model"):
        level = 2
    if level >= 2 and _present(modules, "products") and _present(modules, "segments"):
        level = 3
    if level >= 3 and _present(modules, "management") and _present(modules, "ownership"):
        level = 4
    if level >= 4 and _present(modules, "competition") and _present(modules, "business_risk"):
        level = 5
    if level >= 5 and _present(modules, "timeline"):
        level = 6
    all_core = all(
        _present(modules, m)
        for m in (
            "identity",
            "business_model",
            "products",
            "segments",
            "customers",
            "management",
            "ownership",
            "capital_allocation",
            "competition",
            "business_quality",
            "business_risk",
            "timeline",
            "knowledge_links",
        )
    )
    if level >= 6 and all_core and gate_pass:
        level = INSTITUTIONAL_COMPLETE_LEVEL

    return {
        "coverage_level": level,
        "coverage_level_name": coverage_level_name(level),
        "complete": level >= INSTITUTIONAL_COMPLETE_LEVEL,
        "levels": COVERAGE_LEVELS,
    }


def intelligence_score(obj: dict[str, Any]) -> float:
    """0–100 score: module presence + known-field ratio (not a reasoning score)."""
    modules = obj.get("modules") or {}
    if not modules:
        return 0.0
    present = sum(1 for v in modules.values() if isinstance(v, dict) and v)
    module_score = 100.0 * present / 13.0
    known = 0
    total = 0
    for mod in modules.values():
        if not isinstance(mod, dict):
            continue
        for cell in (mod.get("fields") or {}).values():
            total += 1
            if isinstance(cell, dict) and cell.get("status") == "known":
                known += 1
    known_score = 100.0 * known / total if total else 0.0
    # Weight presence higher so Level path progresses even with UNKNOWN fields
    return round(0.65 * module_score + 0.35 * known_score, 2)
