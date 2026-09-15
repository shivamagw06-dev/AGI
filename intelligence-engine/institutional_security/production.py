"""PRP-02 production façades — auth / context / audit / API keys / Security Center."""

from __future__ import annotations

from typing import Any, Optional

from institutional_security import api_keys as keys_mod
from institutional_security import audit as audit_mod
from institutional_security import authentication as authn
from institutional_security import permissions as perms_mod
from institutional_security import session as session_mod
from institutional_security import tenant as tenant_mod
from institutional_security.correlation import attach_correlation
from institutional_security.diagnostics import build_diagnostics, security_center_board
from institutional_security.flags import flags_dict, is_enabled
from institutional_security.gateway import attach_security_envelope, gate
from institutional_security.roles import list_roles
from institutional_security.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PRP_PRODUCT,
    PRP_ROLE,
    PRP_SPEC,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
    SECURITY_ENGINE_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    authn.reset_for_tests()
    session_mod.reset_for_tests()
    keys_mod.reset_for_tests()
    audit_mod.reset_for_tests()
    perms_mod.reset_for_tests()
    tenant_mod.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "role": PRP_ROLE,
        "llm": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "security_engine_version": SECURITY_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "enters_intelligence_layer": False,
        "complements_execution_context": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PRP_SPEC,
        "brand": "AGI",
        "programme": "PRP",
        "phase": "production_readiness",
        "as_of": now_iso(),
        **security_center_board(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    board = security_center_board()
    return {
        "status": h.get("status"),
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "llm": False,
        "security_center": True,
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "enters_intelligence_layer": False,
        **board,
    }


def login(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": PRP_WORKSTREAM_ID}
    body = dict(payload or {})
    cid = attach_correlation(body)
    method = str(body.get("method") or body.get("authentication_method") or "password").lower()

    if method == "api_key":
        identity, err = authn.authenticate_api_key(
            str(body.get("api_key") or body.get("key") or ""),
            correlation_id=cid,
        )
    elif method in {"sso", "oauth2", "oidc"}:
        identity, err = authn.authenticate_sso_oidc(
            method=method,
            subject=str(body.get("subject") or body.get("user_id") or ""),
            claims=body.get("claims") if isinstance(body.get("claims"), dict) else body,
            correlation_id=cid,
        )
    elif method == "service_account":
        identity, err = authn.authenticate_service_account(
            str(body.get("client_id") or body.get("username") or ""),
            str(body.get("client_secret") or body.get("password") or ""),
            correlation_id=cid,
        )
    else:
        identity, err = authn.authenticate_password(
            str(body.get("username") or body.get("user_id") or ""),
            str(body.get("password") or ""),
            correlation_id=cid,
        )

    if err or not identity:
        audit_mod.emit(
            action="auth.login",
            resource="session",
            outcome="failure",
            correlation_id=cid,
            metadata={"method": method, "reason": err},
        )
        return {
            "ok": False,
            "rejected": True,
            "error": "authentication_failed",
            "reason": err,
            "correlation_id": cid,
            "workstream_id": PRP_WORKSTREAM_ID,
        }

    from institutional_security.authorization import build_security_context

    ctx = build_security_context(
        user_id=str(identity["user_id"]),
        tenant_id=str(identity["tenant_id"]),
        role=str(identity["role"]),
        authentication_method=str(identity.get("authentication_method") or method),
        api_key_id=str(identity.get("api_key_id") or ""),
        session_id=str(identity.get("session_id") or ""),
        correlation_id=cid,
        permissions_override=list(identity.get("permissions") or []) or None,
    )
    audit_mod.emit(
        action="auth.login",
        resource="session",
        resource_id=ctx.session_id,
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        outcome="success",
        correlation_id=cid,
        metadata={"method": method},
    )
    result = {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "session_id": ctx.session_id,
        "expires_at": identity.get("expires_at"),
        "security_context": ctx.to_dict(),
        "correlation_id": cid,
        "authentication_method": ctx.authentication_method,
    }
    try:
        from institutional_launch.production import maybe_track_login

        maybe_track_login(body, result)
    except Exception:
        pass
    return result


def logout(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    cid = attach_correlation(body)
    sid = str(body.get("session_id") or "")
    ok = session_mod.revoke_session(sid, reason="logout")
    audit_mod.emit(
        action="auth.logout",
        resource="session",
        resource_id=sid,
        user_id=str(body.get("user_id") or ""),
        tenant_id=str(body.get("tenant_id") or ""),
        outcome="success" if ok else "failure",
        correlation_id=cid,
    )
    return {"ok": ok, "session_id": sid, "correlation_id": cid, "workstream_id": PRP_WORKSTREAM_ID}


def refresh(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    cid = attach_correlation(body)
    row = session_mod.refresh_session(str(body.get("session_id") or ""))
    if not row:
        return {
            "ok": False,
            "error": "session revoked or expired",
            "correlation_id": cid,
            "workstream_id": PRP_WORKSTREAM_ID,
        }
    audit_mod.emit(
        action="auth.refresh",
        resource="session",
        resource_id=row["session_id"],
        user_id=str(row.get("user_id") or ""),
        tenant_id=str(row.get("tenant_id") or ""),
        outcome="success",
        correlation_id=cid,
    )
    return {
        "ok": True,
        "session_id": row["session_id"],
        "expires_at": row["expires_at"],
        "correlation_id": cid,
        "workstream_id": PRP_WORKSTREAM_ID,
    }


def get_context(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    g = gate(payload or {}, operation="audit.read", resource="security", audit=False)
    if not g.get("ok"):
        return g
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "security_context": g.get("security_context"),
        "correlation_id": g.get("correlation_id"),
        "complements_execution_context": True,
        "enters_intelligence_layer": False,
    }


def list_audit(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    g = gate(body, operation="audit.read", resource="audit")
    if not g.get("ok"):
        return g
    events = audit_mod.list_events(
        limit=int(body.get("limit") or 50),
        tenant_id=str(body.get("tenant_id") or ""),
        user_id=str(body.get("user_id") or ""),
        action=str(body.get("action") or ""),
        correlation_id=str(body.get("correlation_id") or ""),
    )
    return attach_security_envelope(
        {
            "ok": True,
            "workstream_id": PRP_WORKSTREAM_ID,
            "events": events,
            "count": len(events),
        },
        g,
    )


def create_api_key(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    g = gate(body, operation="security.manage", resource="api_key")
    if not g.get("ok"):
        return g
    ctx = g["security_context"] or {}
    created = keys_mod.create_api_key(
        user_id=str(body.get("user_id") or ctx.get("user_id") or ""),
        tenant_id=str(body.get("tenant_id") or ctx.get("tenant_id") or ""),
        kind=str(body.get("kind") or "user"),
        permissions=body.get("permissions"),
        ttl_seconds=int(body.get("ttl_seconds") or 86400 * 90),
        label=str(body.get("label") or ""),
    )
    audit_mod.emit(
        action="api_key.create",
        resource="api_key",
        resource_id=str(created.get("api_key_id") or ""),
        user_id=str(ctx.get("user_id") or ""),
        tenant_id=str(ctx.get("tenant_id") or ""),
        outcome="success",
        correlation_id=str(g.get("correlation_id") or ""),
        metadata={"kind": created.get("kind")},
    )
    return attach_security_envelope({**created, "workstream_id": PRP_WORKSTREAM_ID}, g)


def revoke_api_key(api_key_id: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    g = gate(body, operation="security.manage", resource="api_key", resource_id=api_key_id)
    if not g.get("ok"):
        return g
    ctx = g["security_context"] or {}
    out = keys_mod.revoke_api_key(api_key_id, reason=str(body.get("reason") or "revoked"))
    audit_mod.emit(
        action="api_key.revoke",
        resource="api_key",
        resource_id=api_key_id,
        user_id=str(ctx.get("user_id") or ""),
        tenant_id=str(ctx.get("tenant_id") or ""),
        outcome="success" if out.get("ok") else "failure",
        correlation_id=str(g.get("correlation_id") or ""),
    )
    return attach_security_envelope({**out, "workstream_id": PRP_WORKSTREAM_ID}, g)


def roles_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "roles": list_roles(),
        "engines_must_not_check": True,
    }


def permissions_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "permissions": perms_mod.list_permissions(),
        "capability_based": True,
    }


def grant_permissions(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    g = gate(body, operation="security.manage", resource="permission")
    if not g.get("ok"):
        return g
    ctx = g["security_context"] or {}
    out = perms_mod.grant(
        str(body.get("user_id") or ""),
        body.get("permissions") or [],
        actor_id=str(ctx.get("user_id") or ""),
    )
    audit_mod.emit(
        action="permission.change",
        resource="permission",
        resource_id=str(body.get("user_id") or ""),
        user_id=str(ctx.get("user_id") or ""),
        tenant_id=str(ctx.get("tenant_id") or ""),
        outcome="success" if out.get("ok") else "failure",
        correlation_id=str(g.get("correlation_id") or ""),
        metadata={"granted": body.get("permissions")},
    )
    return attach_security_envelope({**out, "workstream_id": PRP_WORKSTREAM_ID}, g)


def tenants_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "tenants": tenant_mod.list_tenants(),
        "intelligence_is_global": True,
        "tenant_data_isolated": True,
    }


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}


# Soft-integration helpers for platform façades (not domain engines)


def _should_gate(payload: dict[str, Any]) -> bool:
    """Gate when enforce mode is on, or when the caller supplied credentials."""
    from institutional_security.flags import enforce_auth
    from institutional_security.gateway import extract_credentials

    if payload.get("_prp_security_bypass") or payload.get("_prp_worker"):
        return False
    if enforce_auth():
        return True
    creds = extract_credentials(payload)
    return bool(
        creds.get("session_id")
        or creds.get("api_key")
        or (creds.get("user_id") and creds.get("tenant_id"))
    )


def maybe_gate_ask(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return rejection dict if gate fails; None if allowed (or security disabled)."""
    if not is_enabled() or not _should_gate(payload):
        return None
    g = gate(payload, operation="ask", resource="ask")
    if not g.get("ok"):
        return g
    payload["_prp_security_gate"] = g
    return None


def maybe_gate_workspace(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not is_enabled() or not _should_gate(payload):
        return None
    g = gate(payload, operation="workspace.read", resource="workspace")
    if not g.get("ok"):
        return g
    payload["_prp_security_gate"] = g
    return None


def maybe_gate_publication(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not is_enabled() or not _should_gate(payload):
        return None
    op = "publication.distribute" if payload.get("distribute_to") else "publication.generate"
    g = gate(payload, operation=op, resource="publication")
    if not g.get("ok"):
        return g
    payload["_prp_security_gate"] = g
    return None


def finalize_with_security(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    g = payload.get("_prp_security_gate")
    if not isinstance(g, dict):
        return result
    out = attach_security_envelope(result, g)
    # Privileged completion audit for publications
    if result.get("ok") and (result.get("publication") or result.get("async")):
        pub = result.get("publication") or {}
        audit_privileged_id = str(pub.get("publication_id") or result.get("job_id") or "")
        action = (
            "publication.distribute"
            if result.get("distribution")
            else "publication.generate"
        )
        audit_mod.emit(
            action=action,
            resource="publication",
            resource_id=audit_privileged_id,
            user_id=str((g.get("security_context") or {}).get("user_id") or ""),
            tenant_id=str((g.get("security_context") or {}).get("tenant_id") or ""),
            outcome="success",
            correlation_id=str(g.get("correlation_id") or ""),
            metadata={"async": bool(result.get("async"))},
        )
    return out
