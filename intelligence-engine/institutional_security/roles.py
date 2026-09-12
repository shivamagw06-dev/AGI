"""RBAC role catalog (PRP-02)."""

from __future__ import annotations

from typing import Any

from institutional_security.schema import ROLE_PERMISSIONS, ROLES


ROLE_ALIASES = {
    "admin": "administrator",
    "cio": "chief_investment_officer",
    "pm": "portfolio_manager",
    "analyst": "research_analyst",
    "research": "research_analyst",
    "ro": "read_only",
    "readonly": "read_only",
    "sa": "service_account",
    "svc": "service_account",
}


def normalize_role(role: str) -> str:
    key = str(role or "read_only").strip().lower().replace(" ", "_").replace("-", "_")
    key = ROLE_ALIASES.get(key, key)
    if key not in ROLE_PERMISSIONS:
        return "read_only"
    return key


def list_roles() -> list[dict[str, Any]]:
    return [
        {
            "role_id": r,
            "permissions": list(ROLE_PERMISSIONS.get(r, ())),
            "affects_authorization_not_intelligence": True,
        }
        for r in ROLES
    ]


def role_permissions(role: str) -> tuple[str, ...]:
    return ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["read_only"])
