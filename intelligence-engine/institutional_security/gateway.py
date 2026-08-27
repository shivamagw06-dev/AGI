"""Security Gateway — wraps platform entry; never enters intelligence layer (PRP-02)."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_security import audit as audit_mod
from institutional_security import authentication as authn
from institutional_security import session as session_mod
from institutional_security.authorization import authorize, build_security_context
from institutional_security.correlation import attach_correlation, ensure_correlation_id
from institutional_security.flags import enforce_auth, is_enabled
from institutional_security.validator import (
    reject_payload,
    validate_execution_context_pair,
    validate_security_context,
)

# Map platform operations → required permission
OPERATION_PERMISSIONS = {
    "ask": "research.read",
    "workspace.read": "research.read",
    "research.note.write": "research.note.write",
    "publication.generate": "publication.generate",
    "publication.distribute": "publication.distribute",
    "committee.approve": "committee.approve",
    "policy.manage": "policy.manage",
    "portfolio.manage": "portfolio.manage",
    "platform.admin": "platform.admin",
    "security.manage": "security.manage",
    "audit.read": "audit.read",
}


def extract_credentials(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    security = body.get("security") if isinstance(body.get("security"), dict) else {}
    headers = body.get("headers") if isinstance(body.get("headers"), dict) else {}
    return {
        "session_id": (
            body.get("session_id")
            or security.get("session_id")
            or headers.get("X-Session-Id")
            or headers.get("x-session-id")
            or ""
        ),
        "api_key": (
            body.get("api_key")
            or security.get("api_key")
            or headers.get("X-API-Key")
            or headers.get("x-api-key")
            or ""
        ),
        "authorization": (
            body.get("authorization")
            or headers.get("Authorization")
            or headers.get("authorization")
            or ""
        ),
        "user_id": body.get("user_id") or security.get("user_id") or "",
        "tenant_id": body.get("tenant_id") or security.get("tenant_id") or "",
        "role": body.get("role") or security.get("role") or "",
        "correlation_id": body.get("correlation_id") or security.get("correlation_id") or "",
        "execution_context": body.get("execution_context")
        if isinstance(body.get("execution_context"), dict)
        else {},
        "portfolio_id": body.get("portfolio_id")
        or (body.get("execution_context") or {}).get("portfolio_id")
        or "",
        "resource_tenant_id": body.get("resource_tenant_id") or security.get("tenant_id") or "",
    }


def authenticate_request(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Resolve identity from session / API key / bearer-style demo token."""
    creds = extract_credentials(payload)
    cid = attach_correlation({"correlation_id": creds.get("correlation_id")})
    t0 = time.perf_counter()

    if creds.get("session_id"):
        identity, err = authn.resolve_session(str(creds["session_id"]))
        if err:
            return reject_payload(err, code="authentication_failed", correlation_id=cid)
        ctx = build_security_context(
            user_id=str(identity["user_id"]),
            tenant_id=str(identity["tenant_id"]),
            role=str(identity["role"]),
            authentication_method=str(identity.get("authentication_method") or "password"),
            session_id=str(identity["session_id"]),
            correlation_id=cid,
        )
        return {
            "ok": True,
            "security_context": ctx.to_dict(),
            "correlation_id": cid,
            "auth_latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    if creds.get("api_key"):
        identity, err = authn.authenticate_api_key(str(creds["api_key"]), correlation_id=cid)
        if err:
            return reject_payload(err, code="authentication_failed", correlation_id=cid)
        ctx = build_security_context(
            user_id=str(identity["user_id"]),
            tenant_id=str(identity["tenant_id"]),
            role=str(identity["role"]),
            authentication_method="api_key",
            api_key_id=str(identity.get("api_key_id") or ""),
            session_id=str(identity.get("session_id") or ""),
            correlation_id=cid,
            permissions_override=list(identity.get("permissions") or []),
        )
        return {
            "ok": True,
            "security_context": ctx.to_dict(),
            "correlation_id": cid,
            "auth_latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # Bearer demo: "Bearer user_id:session_or_password" not used — fall through to soft demo
    if creds.get("user_id") and creds.get("tenant_id"):
        ctx = build_security_context(
            user_id=str(creds["user_id"]),
            tenant_id=str(creds["tenant_id"]),
            role=str(creds.get("role") or "research_analyst"),
            authentication_method="password",
            correlation_id=cid,
        )
        return {
            "ok": True,
            "security_context": ctx.to_dict(),
            "correlation_id": cid,
            "auth_latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "soft_identity": True,
        }

    if not enforce_auth():
        # Dev soft-allow anonymous with read_only in default tenant
        ctx = build_security_context(
            user_id="anonymous.demo",
            tenant_id="agi-default",
            role="read_only",
            authentication_method="password",
            correlation_id=cid,
        )
        return {
            "ok": True,
            "security_context": ctx.to_dict(),
            "correlation_id": cid,
            "auth_latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "anonymous": True,
        }

    return reject_payload(
        "authentication required",
        code="authentication_failed",
        correlation_id=cid,
    )


def gate(
    payload: Optional[dict[str, Any]] = None,
    *,
    operation: str,
    resource: str = "platform",
    resource_id: str = "",
    audit: bool = True,
) -> dict[str, Any]:
    """
    Authenticate + authorize before platform orchestration.
    Returns {ok, security_context, correlation_id} or rejection payload.
    """
    if not is_enabled():
        cid = ensure_correlation_id()
        return {
            "ok": True,
            "enabled": False,
            "correlation_id": cid,
            "security_context": None,
            "bypassed": True,
        }

    auth = authenticate_request(payload)
    if not auth.get("ok"):
        if audit:
            audit_mod.emit(
                action=operation,
                resource=resource,
                resource_id=resource_id,
                outcome="denied",
                correlation_id=str(auth.get("correlation_id") or ""),
                metadata={"reason": auth.get("reason"), "gate": "authentication"},
            )
        return auth

    ctx_d = dict(auth["security_context"] or {})
    v = validate_security_context(ctx_d)
    if not v["ok"] and enforce_auth():
        return reject_payload(
            "; ".join(v["errors"]),
            code="invalid_security_context",
            correlation_id=str(auth.get("correlation_id") or ""),
        )

    creds = extract_credentials(payload)
    pair = validate_execution_context_pair(ctx_d, creds.get("execution_context"))
    if not pair["ok"]:
        return reject_payload(
            "; ".join(pair["errors"]),
            code="invalid_execution_context",
            correlation_id=str(auth.get("correlation_id") or ""),
        )

    needed = OPERATION_PERMISSIONS.get(operation, "research.read")
    from institutional_security.models import InstitutionalSecurityContext

    ctx = InstitutionalSecurityContext(
        user_id=str(ctx_d.get("user_id") or ""),
        tenant_id=str(ctx_d.get("tenant_id") or ""),
        role=str(ctx_d.get("role") or "read_only"),
        permissions=tuple(ctx_d.get("permissions") or ()),
        authentication_method=str(ctx_d.get("authentication_method") or "password"),
        api_key_id=str(ctx_d.get("api_key_id") or ""),
        session_id=str(ctx_d.get("session_id") or ""),
        correlation_id=str(auth.get("correlation_id") or ""),
    )

    resource_tenant = str(creds.get("resource_tenant_id") or ctx.tenant_id)
    ok, err = authorize(
        ctx,
        permission=needed,
        resource_tenant_id=resource_tenant,
        resource_kind=resource,
        portfolio_id=str(creds.get("portfolio_id") or ""),
    )
    if not ok:
        if audit:
            audit_mod.emit(
                action=operation,
                resource=resource,
                resource_id=resource_id,
                user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                outcome="denied",
                correlation_id=ctx.correlation_id,
                metadata={"reason": err, "permission": needed},
            )
        return reject_payload(
            err or "insufficient permission",
            code="insufficient_permission",
            correlation_id=ctx.correlation_id,
            extra={"permission": needed, "security_context": ctx.to_dict()},
        )

    if audit:
        audit_mod.emit(
            action=operation,
            resource=resource,
            resource_id=resource_id,
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            outcome="authorized",
            correlation_id=ctx.correlation_id,
            metadata={"permission": needed},
        )

    return {
        "ok": True,
        "security_context": ctx.to_dict(),
        "correlation_id": ctx.correlation_id,
        "permission": needed,
        "auth_latency_ms": auth.get("auth_latency_ms"),
        "enters_intelligence_layer": False,
    }


def attach_security_envelope(result: dict[str, Any], gate_result: dict[str, Any]) -> dict[str, Any]:
    """Attach security + correlation to an orchestration response without mutating meaning."""
    out = dict(result or {})
    out["security_context"] = gate_result.get("security_context")
    out["correlation_id"] = gate_result.get("correlation_id")
    out["security_gate"] = {
        "ok": gate_result.get("ok"),
        "permission": gate_result.get("permission"),
        "workstream_id": "PRP-02",
        "enters_intelligence_layer": False,
    }
    return out


def audit_privileged(
    *,
    action: str,
    resource: str,
    resource_id: str = "",
    security_context: Optional[dict[str, Any]] = None,
    outcome: str = "success",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    ctx = dict(security_context or {})
    event = audit_mod.emit(
        action=action,
        resource=resource,
        resource_id=resource_id,
        user_id=str(ctx.get("user_id") or ""),
        tenant_id=str(ctx.get("tenant_id") or ""),
        outcome=outcome,
        correlation_id=str(ctx.get("correlation_id") or ""),
        metadata=metadata,
    )
    return event.to_dict()
