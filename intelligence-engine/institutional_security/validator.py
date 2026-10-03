"""Quality gates for security requests (PRP-02)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_security import audit as audit_mod
from institutional_security import session as session_mod
from institutional_security.flags import audit_required_for_privileged
from institutional_security.models import InstitutionalSecurityContext
from institutional_security.schema import PRIVILEGED_ACTIONS


def validate_security_context(ctx: InstitutionalSecurityContext | dict[str, Any]) -> dict[str, Any]:
    d = ctx.to_dict() if isinstance(ctx, InstitutionalSecurityContext) else dict(ctx or {})
    errors: list[str] = []
    if not d.get("user_id"):
        errors.append("user_id required")
    if not d.get("tenant_id"):
        errors.append("tenant_id required")
    if not d.get("role"):
        errors.append("role required")
    if d.get("session_id"):
        if not session_mod.get_session(str(d["session_id"])):
            errors.append("revoked or expired session")
    return {
        "ok": not errors,
        "errors": errors,
        "gates": {
            "has_identity": bool(d.get("user_id")),
            "has_tenant": bool(d.get("tenant_id")),
            "session_valid": "revoked or expired session" not in errors,
        },
    }


def validate_execution_context_pair(
    security: dict[str, Any] | None,
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Execution context must not contradict security tenant/user when both present."""
    errors: list[str] = []
    sec = dict(security or {})
    exe = dict(execution or {})
    if sec and exe:
        if exe.get("user_id") and sec.get("user_id") and exe["user_id"] != sec["user_id"]:
            errors.append("execution context user_id mismatches security context")
        # role_id in execution is workflow hint; security role is authoritative for authz
    return {"ok": not errors, "errors": errors}


def validate_privileged_audit(
    *,
    action: str,
    resource_id: str = "",
    correlation_id: str = "",
) -> dict[str, Any]:
    if action not in PRIVILEGED_ACTIONS:
        return {"ok": True, "required": False}
    if not audit_required_for_privileged():
        return {"ok": True, "required": False, "skipped": True}
    ok = audit_mod.has_audit_for_action(
        action=action,
        resource_id=resource_id,
        correlation_id=correlation_id,
    )
    return {
        "ok": ok,
        "required": True,
        "errors": [] if ok else [f"missing audit event for privileged action: {action}"],
    }


def reject_payload(
    reason: str,
    *,
    code: str = "forbidden",
    correlation_id: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    out = {
        "ok": False,
        "rejected": True,
        "workstream_id": "PRP-02",
        "error": code,
        "reason": reason,
        "correlation_id": correlation_id or None,
        "enters_intelligence_layer": False,
    }
    if extra:
        out.update(extra)
    return out
