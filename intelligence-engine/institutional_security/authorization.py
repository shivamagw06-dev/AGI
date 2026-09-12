"""Authorization engine — who may perform an operation (PRP-02)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_security.models import InstitutionalSecurityContext
from institutional_security.permissions import assert_permission, resolve_permissions
from institutional_security.roles import normalize_role
from institutional_security.tenant import assert_tenant_access, tenant_owns_portfolio


def build_security_context(
    *,
    user_id: str,
    tenant_id: str,
    role: str,
    authentication_method: str = "password",
    api_key_id: str = "",
    session_id: str = "",
    correlation_id: str = "",
    permissions_override: Optional[list[str]] = None,
) -> InstitutionalSecurityContext:
    role_n = normalize_role(role)
    perms = resolve_permissions(
        role=role_n,
        user_id=user_id,
        extra=permissions_override,
    )
    return InstitutionalSecurityContext(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role_n,
        permissions=perms,
        authentication_method=authentication_method,
        api_key_id=api_key_id or "",
        session_id=session_id or "",
        correlation_id=correlation_id or "",
        diagnostics={
            "enters_intelligence_layer": False,
            "authorization_only": True,
        },
    )


def authorize(
    ctx: InstitutionalSecurityContext,
    *,
    permission: str,
    resource_tenant_id: str = "",
    resource_kind: str = "resource",
    portfolio_id: str = "",
) -> tuple[bool, Optional[str]]:
    ok, err = assert_permission(ctx.permissions, permission)
    if not ok:
        return False, err
    if resource_tenant_id:
        tok, terr = assert_tenant_access(
            tenant_id=ctx.tenant_id,
            resource_tenant_id=resource_tenant_id,
            resource_kind=resource_kind,
        )
        if not tok:
            return False, terr
    if portfolio_id and resource_kind in {"portfolio", "workspace", "publication"}:
        # Soft check — unknown portfolios are not hard-failed unless tenant has a catalog
        from institutional_security.tenant import get_tenant

        t = get_tenant(ctx.tenant_id)
        if t and t.portfolio_ids and not tenant_owns_portfolio(ctx.tenant_id, portfolio_id):
            return False, f"tenant mismatch: portfolio {portfolio_id} not in tenant"
    return True, None


def authorize_dict(ctx_dict: dict[str, Any], **kwargs: Any) -> tuple[bool, Optional[str]]:
    ctx = InstitutionalSecurityContext(
        user_id=str(ctx_dict.get("user_id") or ""),
        tenant_id=str(ctx_dict.get("tenant_id") or ""),
        role=str(ctx_dict.get("role") or "read_only"),
        permissions=tuple(ctx_dict.get("permissions") or ()),
        authentication_method=str(ctx_dict.get("authentication_method") or "password"),
        api_key_id=str(ctx_dict.get("api_key_id") or ""),
        session_id=str(ctx_dict.get("session_id") or ""),
        correlation_id=str(ctx_dict.get("correlation_id") or ""),
    )
    return authorize(ctx, **kwargs)
