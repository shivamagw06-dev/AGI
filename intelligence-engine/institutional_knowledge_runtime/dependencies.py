"""Dependency resolution and state propagation."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.schema import DEPENDENCY_DOWNGRADE_STATES


def resolve_dependencies(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Propagate dependency state changes to dependent assertions."""
    by_id: dict[str, dict[str, Any]] = {
        str(a.get("assertion_id")): dict(a) for a in assertions if a.get("assertion_id")
    }

    changed = True
    while changed:
        changed = False
        for aid, assertion in list(by_id.items()):
            deps = assertion.get("dependencies") or []
            if not deps:
                continue
            bad_deps = [
                d for d in deps
                if str(d) in by_id and str(by_id[str(d)].get("status") or "") in DEPENDENCY_DOWNGRADE_STATES
            ]
            if not bad_deps:
                continue
            current = str(assertion.get("status") or "UNKNOWN")
            if current in {"SUPPORTED", "PARTIAL"}:
                updated = dict(assertion)
                updated["status"] = "UNDER_REVIEW"
                updated["_dependency_trigger"] = bad_deps
                by_id[aid] = updated
                changed = True

    return list(by_id.values())
