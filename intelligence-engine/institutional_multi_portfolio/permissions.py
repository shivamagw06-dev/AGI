"""MPC-01 Permissions — separate from data. Engines must not check permissions directly."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio.schema import PERMISSIONS, ROLE_PERMISSIONS, ROLES

_OVERRIDES: dict[str, tuple[str, ...]] = {}  # user_id → extra permissions


def reset_for_tests() -> None:
    _OVERRIDES.clear()


def list_roles() -> list[dict[str, Any]]:
    return [
        {
            "role_id": r,
            "permissions": list(ROLE_PERMISSIONS.get(r, ())),
            "affects_workflow_not_intelligence": True,
        }
        for r in ROLES
    ]


def permissions_for_role(role_id: str) -> tuple[str, ...]:
    key = str(role_id or "analyst").strip().lower().replace(" ", "_")
    aliases = {"pm": "portfolio_manager", "admin": "administrator", "sa": "senior_analyst"}
    key = aliases.get(key, key)
    if key not in ROLE_PERMISSIONS:
        key = "analyst"
    return ROLE_PERMISSIONS[key]


def resolve_permissions(
    *,
    role_id: str = "analyst",
    user_id: str = "",
    extra: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    base = list(permissions_for_role(role_id))
    if user_id and user_id in _OVERRIDES:
        base.extend(_OVERRIDES[user_id])
    if extra:
        base.extend(extra)
    # Dedupe preserving order
    return tuple(dict.fromkeys(p for p in base if p in PERMISSIONS))


def grant(user_id: str, permissions: list[str] | tuple[str, ...]) -> dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"ok": False, "error": "user_id required"}
    allowed = tuple(p for p in permissions if p in PERMISSIONS)
    prev = list(_OVERRIDES.get(uid, ()))
    _OVERRIDES[uid] = tuple(dict.fromkeys([*prev, *allowed]))
    return {
        "ok": True,
        "user_id": uid,
        "permissions": list(_OVERRIDES[uid]),
        "separate_from_data": True,
        "engines_must_not_check_directly": True,
    }


def has_permission(permissions: tuple[str, ...] | list[str], needed: str) -> bool:
    return needed in set(permissions)


def assert_permission(
    permissions: tuple[str, ...] | list[str],
    needed: str,
) -> tuple[bool, Optional[str]]:
    if has_permission(permissions, needed):
        return True, None
    return False, f"missing permission: {needed}"
