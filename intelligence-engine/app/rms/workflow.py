"""RMS lifecycle transitions and status helpers."""

from __future__ import annotations

import datetime as _dt

from app.rms.models import (
    PublishingHistoryEntry,
    ResearchObject,
    ResearchStatus,
    TRANSITIONS,
)


class WorkflowError(ValueError):
    pass


def transition(obj: ResearchObject, new_status: ResearchStatus, *, actor: str, details: dict | None = None) -> ResearchObject:
    allowed = TRANSITIONS.get(obj.status, set())
    if new_status != obj.status and new_status not in allowed:
        raise WorkflowError(f"Cannot transition {obj.status.value} → {new_status.value}")
    obj.status = new_status
    obj.updated_at = _dt.datetime.now(_dt.timezone.utc)
    obj.publishing_history.append(
        PublishingHistoryEntry(
            action=f"status:{new_status.value}",
            actor=actor,
            details=details or {},
        )
    )
    return obj


def bump_version(obj: ResearchObject, *, actor: str, reason: str = "revision") -> ResearchObject:
    obj.version += 1
    obj.updated_at = _dt.datetime.now(_dt.timezone.utc)
    obj.publishing_history.append(
        PublishingHistoryEntry(
            action="version_bump",
            actor=actor,
            details={"version": obj.version, "reason": reason},
        )
    )
    obj.compliance.document_versions.append(f"v{obj.version}")
    return obj
