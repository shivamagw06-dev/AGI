"""Session lifecycle — login / logout / refresh / expire / impersonation (PRP-02)."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_security.encryption import encrypt_at_rest, new_token
from institutional_security.schema import DEFAULT_SESSION_TTL_SECONDS

_SESSIONS: dict[str, dict[str, Any]] = {}
_BY_USER: dict[str, set[str]] = {}
_REVOKED: set[str] = set()
_LOGIN_FAILURES = 0
_LOGIN_OK = 0


def reset_for_tests() -> None:
    global _LOGIN_FAILURES, _LOGIN_OK
    _SESSIONS.clear()
    _BY_USER.clear()
    _REVOKED.clear()
    _LOGIN_FAILURES = 0
    _LOGIN_OK = 0


def _now() -> float:
    return time.time()


def create_session(
    *,
    user_id: str,
    tenant_id: str,
    role: str,
    authentication_method: str,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    impersonator_id: str = "",
    correlation_id: str = "",
) -> dict[str, Any]:
    global _LOGIN_OK
    sid = new_token("sess")
    now = _now()
    row = {
        "session_id": sid,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "authentication_method": authentication_method,
        "created_at": now,
        "expires_at": now + int(ttl_seconds),
        "refreshed_at": now,
        "status": "active",
        "impersonator_id": impersonator_id or None,
        "correlation_id": correlation_id,
        "token_sealed": encrypt_at_rest(sid),
    }
    _SESSIONS[sid] = row
    _BY_USER.setdefault(user_id, set()).add(sid)
    _LOGIN_OK += 1
    return dict(row)


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    sid = str(session_id or "")
    if not sid or sid in _REVOKED:
        return None
    row = _SESSIONS.get(sid)
    if not row:
        return None
    if row.get("status") != "active":
        return None
    if float(row.get("expires_at") or 0) < _now():
        row["status"] = "expired"
        return None
    return dict(row)


def refresh_session(session_id: str, *, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> Optional[dict[str, Any]]:
    row = get_session(session_id)
    if not row:
        return None
    now = _now()
    stored = _SESSIONS[session_id]
    stored["expires_at"] = now + int(ttl_seconds)
    stored["refreshed_at"] = now
    return dict(stored)


def revoke_session(session_id: str, *, reason: str = "logout") -> bool:
    sid = str(session_id or "")
    if not sid:
        return False
    _REVOKED.add(sid)
    if sid in _SESSIONS:
        _SESSIONS[sid]["status"] = "revoked"
        _SESSIONS[sid]["revoke_reason"] = reason
    return True


def record_login_failure() -> None:
    global _LOGIN_FAILURES
    _LOGIN_FAILURES += 1


def active_sessions() -> list[dict[str, Any]]:
    out = []
    for sid, row in list(_SESSIONS.items()):
        if get_session(sid):
            out.append(dict(row))
    return out


def sessions_for_user(user_id: str) -> list[dict[str, Any]]:
    return [s for s in active_sessions() if s.get("user_id") == user_id]


def session_metrics() -> dict[str, Any]:
    return {
        "active_sessions": len(active_sessions()),
        "login_ok": _LOGIN_OK,
        "login_failures": _LOGIN_FAILURES,
        "revoked_tokens": len(_REVOKED),
        "total_sessions": len(_SESSIONS),
    }
