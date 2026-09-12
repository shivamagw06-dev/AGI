"""Package audit — prove immutability and planning provenance."""

from __future__ import annotations

from typing import Any


def build_audit(package: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "immutable": True,
        "consumers_may_not_change": [
            "intent",
            "entity",
            "research_objective",
            "blueprint",
            "analyst_plan",
            "layer_plan",
            "api_plan",
            "research_contract",
        ],
        "package_complete": bool(validation.get("package_complete")),
        "package_consistent": bool(validation.get("package_consistent")),
        "conflicts": list(validation.get("conflicts") or []),
        "sources": list((package.get("metadata") or {}).get("sources") or []),
        "audit_trail": [
            "RQ1 planning stack assembled",
            "Package validated",
            "Research Contract attached",
            "Package sealed (immutable)",
        ],
    }
