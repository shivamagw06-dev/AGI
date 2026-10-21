"""Tenant isolation — tenant-owned data isolated; intelligence remains global (PRP-02)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_security.models import InstitutionalTenant

_TENANTS: dict[str, InstitutionalTenant] = {}
_USER_TENANT: dict[str, str] = {}


def reset_for_tests() -> None:
    _TENANTS.clear()
    _USER_TENANT.clear()
    seed_defaults()


def seed_defaults() -> None:
    if "agi-default" in _TENANTS:
        return
    register_tenant(
        {
            "tenant_id": "agi-default",
            "name": "AGI Default Tenant",
            "user_ids": ["analyst.demo", "pm.demo", "cio.demo", "admin.demo"],
            "portfolio_ids": ["agi-core-equity", "growth-portfolio", "income-portfolio"],
            "client_ids": ["client-alpha", "client-beta"],
        }
    )
    register_tenant(
        {
            "tenant_id": "tenant-beta",
            "name": "Beta Family Office",
            "user_ids": ["analyst.beta"],
            "portfolio_ids": ["beta-equity"],
            "client_ids": ["client-beta-fo"],
        }
    )


def register_tenant(payload: dict[str, Any]) -> InstitutionalTenant:
    tid = str(payload.get("tenant_id") or "").strip() or "tenant-unknown"
    t = InstitutionalTenant(
        tenant_id=tid,
        name=str(payload.get("name") or tid),
        status=str(payload.get("status") or "active"),
        user_ids=tuple(payload.get("user_ids") or ()),
        client_ids=tuple(payload.get("client_ids") or ()),
        portfolio_ids=tuple(payload.get("portfolio_ids") or ()),
    )
    _TENANTS[tid] = t
    for uid in t.user_ids:
        _USER_TENANT[uid] = tid
    return t


def get_tenant(tenant_id: str) -> Optional[InstitutionalTenant]:
    return _TENANTS.get(str(tenant_id or ""))


def list_tenants() -> list[dict[str, Any]]:
    return [t.to_dict() for t in _TENANTS.values()]


def resolve_tenant_for_user(user_id: str) -> Optional[InstitutionalTenant]:
    tid = _USER_TENANT.get(str(user_id or ""))
    if not tid:
        return get_tenant("agi-default")
    return get_tenant(tid)


def assert_tenant_access(
    *,
    tenant_id: str,
    resource_tenant_id: str,
    resource_kind: str = "resource",
) -> tuple[bool, Optional[str]]:
    """Tenant-owned resources must match; global intelligence is never tenant-gated here."""
    if resource_kind in {"intelligence", "company", "evidence", "graph"}:
        return True, None
    if not tenant_id or not resource_tenant_id:
        return False, "tenant mismatch: missing tenant"
    if tenant_id != resource_tenant_id:
        return False, f"tenant mismatch: {tenant_id} != {resource_tenant_id}"
    return True, None


def tenant_owns_portfolio(tenant_id: str, portfolio_id: str) -> bool:
    t = get_tenant(tenant_id)
    if not t:
        return False
    return portfolio_id in set(t.portfolio_ids)


# Seed on import for demo readiness
seed_defaults()
