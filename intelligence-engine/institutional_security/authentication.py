"""Authentication — establishes identity only (PRP-02)."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_security import api_keys as keys_mod
from institutional_security import session as session_mod
from institutional_security.encryption import hash_secret, verify_secret
from institutional_security.roles import normalize_role
from institutional_security.schema import AUTH_METHODS
from institutional_security.tenant import resolve_tenant_for_user, seed_defaults

# Demo identity store (password hashes). SSO/OAuth/OIDC resolve via token claims.
_USERS: dict[str, dict[str, Any]] = {}
_AUTH_LATENCY: list[float] = []


def reset_for_tests() -> None:
    _USERS.clear()
    _AUTH_LATENCY.clear()
    seed_demo_users()


def seed_demo_users() -> None:
    if _USERS:
        return
    demos = [
        ("admin.demo", "administrator", "agi-default", "admin-pass"),
        ("cio.demo", "chief_investment_officer", "agi-default", "cio-pass"),
        ("pm.demo", "portfolio_manager", "agi-default", "pm-pass"),
        ("analyst.demo", "research_analyst", "agi-default", "analyst-pass"),
        ("compliance.demo", "compliance", "agi-default", "comp-pass"),
        ("readonly.demo", "read_only", "agi-default", "ro-pass"),
        ("svc.demo", "service_account", "agi-default", "svc-pass"),
        ("analyst.beta", "research_analyst", "tenant-beta", "beta-pass"),
    ]
    for uid, role, tenant, password in demos:
        _USERS[uid] = {
            "user_id": uid,
            "role": role,
            "tenant_id": tenant,
            "password_hash": hash_secret(password),
            "status": "active",
            "auth_methods": list(AUTH_METHODS),
        }
    seed_defaults()


def register_user(
    user_id: str,
    *,
    role: str,
    tenant_id: str,
    password: str,
) -> dict[str, Any]:
    uid = str(user_id or "").strip()
    _USERS[uid] = {
        "user_id": uid,
        "role": normalize_role(role),
        "tenant_id": tenant_id,
        "password_hash": hash_secret(password),
        "status": "active",
        "auth_methods": list(AUTH_METHODS),
    }
    return {"ok": True, "user_id": uid, "role": normalize_role(role), "tenant_id": tenant_id}


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    _AUTH_LATENCY.append(time.perf_counter() - t0)
    return out


def authenticate_password(
    username: str,
    password: str,
    *,
    correlation_id: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    def _do():
        user = _USERS.get(str(username or "").strip())
        if not user or user.get("status") != "active":
            session_mod.record_login_failure()
            return None, "authentication failed"
        if not verify_secret(password, str(user.get("password_hash") or "")):
            session_mod.record_login_failure()
            return None, "authentication failed"
        sess = session_mod.create_session(
            user_id=user["user_id"],
            tenant_id=user["tenant_id"],
            role=user["role"],
            authentication_method="password",
            correlation_id=correlation_id,
        )
        return {
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "role": user["role"],
            "authentication_method": "password",
            "session_id": sess["session_id"],
            "expires_at": sess["expires_at"],
        }, None

    return _timed(_do)


def authenticate_sso_oidc(
    *,
    method: str,
    subject: str,
    claims: Optional[dict[str, Any]] = None,
    correlation_id: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """SSO / OAuth2 / OIDC — trust external IdP claims, map to local identity."""

    def _do():
        m = str(method or "oidc").lower()
        if m not in {"sso", "oauth2", "oidc"}:
            return None, f"unsupported auth method: {m}"
        claims_d = dict(claims or {})
        uid = str(claims_d.get("user_id") or claims_d.get("sub") or subject or "").strip()
        if not uid:
            session_mod.record_login_failure()
            return None, "authentication failed"
        user = _USERS.get(uid)
        if not user:
            # Just-in-time provision from claims
            role = normalize_role(str(claims_d.get("role") or "read_only"))
            tenant = resolve_tenant_for_user(uid)
            tid = str(claims_d.get("tenant_id") or (tenant.tenant_id if tenant else "agi-default"))
            register_user(uid, role=role, tenant_id=tid, password=new_ephemeral_password())
            user = _USERS[uid]
        sess = session_mod.create_session(
            user_id=user["user_id"],
            tenant_id=user["tenant_id"],
            role=user["role"],
            authentication_method=m,
            correlation_id=correlation_id,
        )
        return {
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "role": user["role"],
            "authentication_method": m,
            "session_id": sess["session_id"],
            "expires_at": sess["expires_at"],
            "claims": {k: claims_d[k] for k in ("email", "name", "iss") if k in claims_d},
        }, None

    return _timed(_do)


def new_ephemeral_password() -> str:
    from institutional_security.encryption import new_token

    return new_token("jit")


def authenticate_api_key(
    api_key: str,
    *,
    correlation_id: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    def _do():
        row, err = keys_mod.authenticate_api_key(api_key)
        if err or not row:
            session_mod.record_login_failure()
            return None, err or "authentication failed"
        sess = session_mod.create_session(
            user_id=str(row["user_id"]),
            tenant_id=str(row["tenant_id"]),
            role="service_account" if row.get("kind") == "service" else "read_only",
            authentication_method="api_key",
            correlation_id=correlation_id,
        )
        return {
            "user_id": row["user_id"],
            "tenant_id": row["tenant_id"],
            "role": sess["role"],
            "authentication_method": "api_key",
            "api_key_id": row["api_key_id"],
            "permissions": list(row.get("permissions") or []),
            "session_id": sess["session_id"],
            "expires_at": sess["expires_at"],
        }, None

    return _timed(_do)


def authenticate_service_account(
    client_id: str,
    client_secret: str,
    *,
    correlation_id: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    # Map service accounts onto demo users with role service_account
    return authenticate_password(
        client_id,
        client_secret,
        correlation_id=correlation_id,
    )


def resolve_session(session_id: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    row = session_mod.get_session(session_id)
    if not row:
        return None, "session revoked or expired"
    return {
        "user_id": row["user_id"],
        "tenant_id": row["tenant_id"],
        "role": row["role"],
        "authentication_method": row.get("authentication_method") or "password",
        "session_id": row["session_id"],
        "impersonator_id": row.get("impersonator_id"),
    }, None


def auth_latency_ms() -> Optional[float]:
    if not _AUTH_LATENCY:
        return None
    return round((sum(_AUTH_LATENCY) / len(_AUTH_LATENCY)) * 1000.0, 2)


# Seed demos on import
seed_demo_users()
