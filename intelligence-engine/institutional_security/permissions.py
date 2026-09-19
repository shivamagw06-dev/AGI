"""Capability-based permissions (PRP-02). Engines must not check these."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from institutional_security.roles import normalize_role, role_permissions
from institutional_security.schema import PERMISSIONS

_OVERRIDES: dict[str, tuple[str, ...]] = {}  # user_id → extra
_REVOKED: dict[str, set[str]] = {}  # user_id → revoked caps


def reset_for_tests() -> None:
    _OVERRIDES.clear()
    _REVOKED.clear()


def list_permissions() -> list[dict[str, Any]]:
    return [
        {
            "permission": p,
            "capability_based": True,
            "engines_must_not_check": True,
        }
        for p in PERMISSIONS
    ]


def resolve_permissions(
    *,
    role: str = "read_only",
    user_id: str = "",
    extra: Iterable[str] | None = None,
) -> tuple[str, ...]:
    base = list(role_permissions(normalize_role(role)))
    if user_id and user_id in _OVERRIDES:
        base.extend(_OVERRIDES[user_id])
    if extra:
        base.extend(extra)
    revoked = _REVOKED.get(user_id or "", set())
    out = [p for p in dict.fromkeys(base) if p in PERMISSIONS and p not in revoked]
    return tuple(out)


def grant(user_id: str, permissions: Iterable[str], *, actor_id: str = "") -> dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"ok": False, "error": "user_id required"}
    allowed = tuple(p for p in permissions if p in PERMISSIONS)
    prev = list(_OVERRIDES.get(uid, ()))
    _OVERRIDES[uid] = tuple(dict.fromkeys([*prev, *allowed]))
    if uid in _REVOKED:
        _REVOKED[uid] -= set(allowed)
    return {
        "ok": True,
        "user_id": uid,
        "permissions": list(_OVERRIDES[uid]),
        "actor_id": actor_id,
        "engines_must_not_check": True,
    }


def revoke(user_id: str, permissions: Iterable[str], *, actor_id: str = "") -> dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"ok": False, "error": "user_id required"}
    _REVOKED.setdefault(uid, set()).update(p for p in permissions if p in PERMISSIONS)
    return {
        "ok": True,
        "user_id": uid,
        "revoked": sorted(_REVOKED[uid]),
        "actor_id": actor_id,
    }


def has_permission(permissions: Iterable[str], needed: str) -> bool:
    return needed in set(permissions)


def assert_permission(
    permissions: Iterable[str],
    needed: str,
) -> tuple[bool, Optional[str]]:
    if has_permission(permissions, needed):
        return True, None
    return False, f"insufficient permission: {needed}"
