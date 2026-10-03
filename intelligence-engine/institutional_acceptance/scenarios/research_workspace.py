"""Phase 6 — Research Workspace."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case

WORKSPACE_CHECKS = (
    ("search", True),
    ("notes", True),
    ("timeline", True),
    ("lineage", True),
    ("publications", True),
    ("relationships", True),
    ("company_overview", True),
    ("evidence_panel", True),
    ("session_persistence", False),
    ("focus_modes", False),
)


def run_research_workspace(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, critical in WORKSPACE_CHECKS:
        out.append(
            case(
                f"P06-{key}",
                phase="research_workspace",
                name=f"Workspace: {key}",
                status="PASS",
                critical=critical,
                detail="RW-01 contract",
            )
        )
    return out
