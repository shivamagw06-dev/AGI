"""Coverage levels 0–7 for Institutional Government Intelligence."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.schema import (
    COVERAGE_LEVELS,
    INSTITUTIONAL_COMPLETE_LEVEL,
    coverage_level_name,
)


def compute_coverage_level(
    *,
    bodies: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    timeline: dict[str, Any] | None,
    quality: dict[str, Any] | None,
) -> dict[str, Any]:
    has_registry = bool(bodies)
    has_policy = bool(policies)
    has_timeline = bool(timeline) and int((timeline or {}).get("policy_count") or 0) > 0
    has_relationships = has_policy and all(isinstance(p.get("relationships"), dict) for p in policies)
    has_transmission = has_policy and all(
        isinstance(p.get("transmission"), dict) for p in policies
    )
    has_replay = has_timeline and all(p.get("available_from") for p in policies)
    has_evidence = has_policy and all(p.get("evidence") for p in policies)
    gate_pass = bool((quality or {}).get("gate_pass"))

    level = 0
    if has_registry:
        level = 0
    if has_registry and has_policy:
        level = 1
    if level >= 1 and has_timeline:
        level = 2
    if level >= 2 and has_relationships:
        level = 3
    if level >= 3 and has_transmission:
        level = 4
    if level >= 4 and has_replay:
        level = 5
    if level >= 5 and has_evidence:
        level = 6
    if level >= 6 and gate_pass:
        level = INSTITUTIONAL_COMPLETE_LEVEL

    return {
        "coverage_level": level,
        "coverage_level_name": coverage_level_name(level),
        "complete": level >= INSTITUTIONAL_COMPLETE_LEVEL,
        "levels": COVERAGE_LEVELS,
    }
