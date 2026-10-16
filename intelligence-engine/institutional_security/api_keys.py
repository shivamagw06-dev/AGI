"""API keys — user / service / read-only, scoped, expire, rotate, revoke (PRP-02)."""

from __future__ import annotations

import time
from typing import Any, Iterable, Optional

from institutional_security.encryption import fingerprint, hash_secret, new_token, verify_secret
from institutional_security.schema import DEFAULT_API_KEY_TTL_SECONDS, PERMISSIONS

_KEYS: dict[str, dict[str, Any]] = {}  # key_id → record
_USAGE = 0


def reset_for_tests() -> None:
    global _USAGE
    _KEYS.clear()
    _USAGE = 0


def create_api_key(
    *,
    user_id: str,
    tenant_id: str,
    kind: str = "user",  # user | service | read_only
    permissions: Iterable[str] | None = None,
    ttl_seconds: int = DEFAULT_API_KEY_TTL_SECONDS,
    label: str = "",
) -> dict[str, Any]:
    kind_n = str(kind or "user").lower()
    if kind_n == "read_only":
        perms = ("research.read", "audit.read")
    elif kind_n == "service":
        perms = tuple(p for p in (permissions or ("research.read", "publication.generate")) if p in PERMISSIONS)
    else:
        perms = tuple(p for p in (permissions or ("research.read",)) if p in PERMISSIONS)

    raw = new_token("agib")
    kid = f"key_{fingerprint(raw)}"
    now = time.time()
    row = {
        "api_key_id": kid,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "kind": kind_n,
        "permissions": list(perms),
        "label": label or kind_n,
        "created_at": now,
        "expires_at": now + int(ttl_seconds),
        "status": "active",
        "secret_hash": hash_secret(raw),
        "fingerprint": fingerprint(raw),
        "last_used_at": None,
        "use_count": 0,
    }
    _KEYS[kid] = row
    # Return raw secret once
    return {
        "ok": True,
        "api_key_id": kid,
        "api_key": raw,
        "kind": kind_n,
        "permissions": list(perms),
        "expires_at": row["expires_at"],
        "tenant_id": tenant_id,
        "user_id": user_id,
        "note": "Store the api_key now; it cannot be retrieved again.",
    }


def authenticate_api_key(raw_key: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    global _USAGE
    raw = str(raw_key or "").strip()
    if not raw:
        return None, "api key required"
    fp = fingerprint(raw)
    for row in _KEYS.values():
        if row.get("fingerprint") != fp:
            continue
        if row.get("status") != "active":
            return None, "api key revoked"
        if float(row.get("expires_at") or 0) < time.time():
            row["status"] = "expired"
            return None, "api key expired"
        if not verify_secret(raw, str(row.get("secret_hash") or "")):
            return None, "api key invalid"
        row["last_used_at"] = time.time()
        row["use_count"] = int(row.get("use_count") or 0) + 1
        _USAGE += 1
        return dict(row), None
    return None, "api key not found"


def revoke_api_key(api_key_id: str, *, reason: str = "revoked") -> dict[str, Any]:
    kid = str(api_key_id or "")
    row = _KEYS.get(kid)
    if not row:
        return {"ok": False, "error": "api_key_not_found"}
    row["status"] = "revoked"
    row["revoke_reason"] = reason
    return {"ok": True, "api_key_id": kid, "status": "revoked"}


def rotate_api_key(api_key_id: str) -> dict[str, Any]:
    row = _KEYS.get(str(api_key_id or ""))
    if not row or row.get("status") != "active":
        return {"ok": False, "error": "api_key_not_found_or_inactive"}
    revoke_api_key(api_key_id, reason="rotated")
    return create_api_key(
        user_id=str(row["user_id"]),
        tenant_id=str(row["tenant_id"]),
        kind=str(row.get("kind") or "user"),
        permissions=list(row.get("permissions") or []),
        label=str(row.get("label") or "") + " (rotated)",
    )


def list_api_keys(*, tenant_id: str = "", user_id: str = "") -> list[dict[str, Any]]:
    out = []
    for row in _KEYS.values():
        if tenant_id and row.get("tenant_id") != tenant_id:
            continue
        if user_id and row.get("user_id") != user_id:
            continue
        public = {k: v for k, v in row.items() if k != "secret_hash"}
        out.append(public)
    return out


def api_key_metrics() -> dict[str, Any]:
    active = sum(1 for r in _KEYS.values() if r.get("status") == "active")
    revoked = sum(1 for r in _KEYS.values() if r.get("status") == "revoked")
    return {
        "api_keys_total": len(_KEYS),
        "api_keys_active": active,
        "api_keys_revoked": revoked,
        "api_key_usage": _USAGE,
    }
