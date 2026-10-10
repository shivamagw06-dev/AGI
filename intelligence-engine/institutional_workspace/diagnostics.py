"""RW-01 diagnostics + workspace health signals."""

from __future__ import annotations

from typing import Any, Optional

from institutional_workspace.models import InstitutionalWorkspace
from institutional_workspace.schema import RW_VERSION, RW_WORKSTREAM_ID, WORKSPACE_ENGINE_VERSION


def build_diagnostics(
    workspace: InstitutionalWorkspace,
    *,
    latency_ms: float = 0.0,
    missing_links: Optional[list[str]] = None,
) -> dict[str, Any]:
    orphan_notes = sum(
        1 for n in workspace.notes if not n.linked_decision_id and not n.linked_object_id
    )
    timeline_gaps = 0
    if len(workspace.timeline) < 2:
        timeline_gaps = 1
    missing_evidence = 0 if workspace.evidence else 1
    broken = list(missing_links or [])
    return {
        "workstream_id": RW_WORKSTREAM_ID,
        "version": RW_VERSION,
        "workspace_engine_version": WORKSPACE_ENGINE_VERSION,
        "workspace_id": workspace.workspace_id,
        "context": workspace.context,
        "latency_ms": round(float(latency_ms), 2),
        "timeline_count": len(workspace.timeline),
        "linked_count": len(workspace.linked_objects),
        "evidence_count": len(workspace.evidence),
        "note_count": len(workspace.notes),
        "missing_links": broken,
        "missing_evidence": missing_evidence,
        "broken_lineage": broken,
        "timeline_gaps": timeline_gaps,
        "orphaned_notes": orphan_notes,
        "navigation_integrity": len(workspace.navigation) >= 5,
        "mutates_system_intelligence": False,
        "presentation_only": True,
    }


def workspace_health_board(rows: list[InstitutionalWorkspace]) -> dict[str, Any]:
    missing_links = 0
    missing_evidence = 0
    timeline_gaps = 0
    orphaned = 0
    for w in rows:
        d = w.diagnostics or {}
        missing_links += len(d.get("missing_links") or [])
        missing_evidence += int(d.get("missing_evidence") or 0)
        timeline_gaps += int(d.get("timeline_gaps") or 0)
        orphaned += int(d.get("orphaned_notes") or 0)
    return {
        "objects_with_missing_links": missing_links,
        "missing_evidence": missing_evidence,
        "broken_lineage": missing_links,
        "timeline_gaps": timeline_gaps,
        "orphaned_notes": orphaned,
        "navigation_integrity": all(
            (w.diagnostics or {}).get("navigation_integrity") for w in rows
        )
        if rows
        else True,
        "workspaces_cached": len(rows),
    }
