"""Role-based permissions for the warehouse.

The admin workspace sits behind the platform's admin gate, so the roles here
divide *what an admin may do*, not whether they are an admin:

    read     see every sheet, search, export
    edit     read + stage imports + edit cells
    approve  edit + commit imports + restore versions
    publish  approve + publish, refresh, delete

Assignment comes from the environment so it can be changed without a deploy:

    WAREHOUSE_READERS / WAREHOUSE_EDITORS / WAREHOUSE_APPROVERS / WAREHOUSE_PUBLISHERS
    WAREHOUSE_DEFAULT_ROLE   (default ``publish`` — matches the existing admin gate)
"""

from __future__ import annotations

import os
from typing import Any, Optional

ROLES = ("read", "edit", "approve", "publish")

_ROLE_ACTIONS: dict[str, set[str]] = {
    "read": {"read", "search", "export", "history"},
    "edit": {"read", "search", "export", "history", "edit", "create", "stage_import", "recalculate"},
    "approve": {"read", "search", "export", "history", "edit", "create", "stage_import",
                "recalculate", "commit_import", "restore", "clear_override", "validate"},
    "publish": {"read", "search", "export", "history", "edit", "create", "stage_import",
                "recalculate", "commit_import", "restore", "clear_override", "validate",
                "publish", "refresh", "delete"},
}

_ENV_BY_ROLE = {
    "read": "WAREHOUSE_READERS",
    "edit": "WAREHOUSE_EDITORS",
    "approve": "WAREHOUSE_APPROVERS",
    "publish": "WAREHOUSE_PUBLISHERS",
}


def _members(role: str) -> set[str]:
    raw = os.getenv(_ENV_BY_ROLE[role], "") or ""
    return {part.strip().lower() for part in raw.replace(";", ",").split(",") if part.strip()}


def default_role() -> str:
    raw = (os.getenv("WAREHOUSE_DEFAULT_ROLE") or "publish").strip().lower()
    return raw if raw in ROLES else "publish"


def role_for(actor: Optional[str]) -> str:
    """Highest role the actor is listed under, else the configured default."""
    identity = (actor or "").strip().lower()
    if identity:
        for role in reversed(ROLES):  # publish first
            if identity in _members(role):
                return role
    return default_role()


def can(actor: Optional[str], action: str) -> bool:
    return action in _ROLE_ACTIONS.get(role_for(actor), set())


def require(actor: Optional[str], action: str) -> Optional[dict[str, Any]]:
    """Return an error payload when the actor may not perform the action."""
    if not (actor or "").strip():
        return {"ok": False, "error": "actor_required",
                "detail": "every warehouse write must name who is making it"}
    if not can(actor, action):
        return {
            "ok": False,
            "error": "forbidden",
            "action": action,
            "role": role_for(actor),
            "detail": f"role '{role_for(actor)}' cannot perform '{action}'",
        }
    return None


def describe(actor: Optional[str]) -> dict[str, Any]:
    role = role_for(actor)
    return {
        "ok": True,
        "actor": actor,
        "role": role,
        "actions": sorted(_ROLE_ACTIONS.get(role, set())),
        "roles": list(ROLES),
        "default_role": default_role(),
    }
