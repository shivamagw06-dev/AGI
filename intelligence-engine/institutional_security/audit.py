"""Immutable append-only audit log (PRP-02)."""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Optional

from institutional_security.correlation import get_correlation_id
from institutional_security.models import InstitutionalAuditEvent

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_EVENTS: list[InstitutionalAuditEvent] = []
_PERMISSION_CHANGES = 0


def reset_for_tests() -> None:
    global _PERMISSION_CHANGES
    with _LOCK:
        _EVENTS.clear()
        _PERMISSION_CHANGES = 0


def _event_id(action: str, resource: str, resource_id: str, ts: str) -> str:
    raw = f"{action}|{resource}|{resource_id}|{ts}|{get_correlation_id()}"
    return f"aud_{hashlib.sha256(raw.encode()).hexdigest()[:14]}"


def emit(
    *,
    action: str,
    resource: str,
    user_id: str = "",
    tenant_id: str = "",
    resource_id: str = "",
    outcome: str = "success",
    correlation_id: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> InstitutionalAuditEvent:
    global _PERMISSION_CHANGES
    ts = now_iso()
    cid = correlation_id or get_correlation_id()
    event = InstitutionalAuditEvent(
        event_id=_event_id(action, resource, resource_id, ts),
        timestamp=ts,
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        outcome=outcome,
        correlation_id=cid,
        metadata=dict(metadata or {}),
    )
    with _LOCK:
        _EVENTS.append(event)
        if action in {"permission.change", "permission.grant", "permission.revoke"}:
            _PERMISSION_CHANGES += 1
    return event


def list_events(
    *,
    limit: int = 50,
    tenant_id: str = "",
    user_id: str = "",
    action: str = "",
    correlation_id: str = "",
) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_EVENTS)
    if tenant_id:
        rows = [e for e in rows if e.tenant_id == tenant_id]
    if user_id:
        rows = [e for e in rows if e.user_id == user_id]
    if action:
        rows = [e for e in rows if e.action == action]
    if correlation_id:
        rows = [e for e in rows if e.correlation_id == correlation_id]
    return [e.to_dict() for e in reversed(rows[-limit:])]


def find_for_resource(resource: str, resource_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        rows = [
            e
            for e in _EVENTS
            if e.resource == resource and e.resource_id == resource_id
        ]
    return [e.to_dict() for e in rows]


def has_audit_for_action(
    *,
    action: str,
    resource_id: str = "",
    correlation_id: str = "",
) -> bool:
    with _LOCK:
        for e in reversed(_EVENTS):
            if e.action != action:
                continue
            if resource_id and e.resource_id != resource_id:
                continue
            if correlation_id and e.correlation_id != correlation_id:
                continue
            return True
    return False


def audit_metrics() -> dict[str, Any]:
    with _LOCK:
        n = len(_EVENTS)
        failures = sum(1 for e in _EVENTS if e.outcome != "success")
    return {
        "audit_volume": n,
        "audit_failures": failures,
        "permission_changes": _PERMISSION_CHANGES,
        "recent": list_events(limit=8),
    }
