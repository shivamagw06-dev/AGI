"""MPC-01 Workspace Resolver — User → Role → Portfolio → Workspace → Ask / Research."""

from __future__ import annotations

import hashlib
from typing import Any, Optional
from urllib.parse import quote

from institutional_multi_portfolio import client_registry as creg
from institutional_multi_portfolio import portfolio_registry as preg
from institutional_multi_portfolio.mandate_engine import resolve_mandate
from institutional_multi_portfolio.models import (
    InstitutionalExecutionContext,
    InstitutionalPortfolioWorkspace,
)
from institutional_multi_portfolio.permissions import resolve_permissions
from institutional_multi_portfolio.schema import PLATFORM_ENGINE_VERSION

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _workspace_id(portfolio_id: str, client_id: str, role_id: str) -> str:
    raw = f"{portfolio_id}|{client_id}|{role_id}|{PLATFORM_ENGINE_VERSION}"
    return f"ws-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def build_execution_context(
    *,
    portfolio_id: str,
    client_id: str = "",
    mandate_id: str = "",
    role_id: str = "analyst",
    user_id: str = "",
) -> InstitutionalExecutionContext:
    rec = preg.get_portfolio(portfolio_id)
    if not rec:
        rec = preg.register_portfolio(portfolio_id, name=portfolio_id, mandate_id=mandate_id or "balanced")
    mandate = resolve_mandate(mandate_id or rec.mandate_id)
    perms = resolve_permissions(role_id=role_id, user_id=user_id)
    wid = _workspace_id(rec.portfolio_id, client_id, role_id)
    return InstitutionalExecutionContext(
        workspace_id=wid,
        portfolio_id=rec.portfolio_id,
        client_id=client_id,
        mandate_id=mandate["mandate_id"],
        role_id=role_id,
        user_id=user_id,
        policy_profile=mandate["policy_profile"],
        permissions=perms,
    )


def resolve_workspace(
    *,
    portfolio_id: str = "agi-core-equity",
    client_id: str = "",
    role_id: str = "analyst",
    user_id: str = "",
    mandate_id: str = "",
    linked_publications: list[str] | tuple[str, ...] | None = None,
) -> InstitutionalPortfolioWorkspace:
    ctx = build_execution_context(
        portfolio_id=portfolio_id,
        client_id=client_id,
        mandate_id=mandate_id,
        role_id=role_id,
        user_id=user_id,
    )
    rec = preg.get_portfolio(ctx.portfolio_id)
    members = tuple(rec.members) if rec else ()
    client = creg.get_client(client_id) if client_id else None
    if client and ctx.portfolio_id not in client.portfolios:
        # Soft: still allow resolve, flag in diagnostics later
        pass

    ask_qs = (
        f"context=portfolio&portfolio={quote(ctx.portfolio_id)}"
        f"&mandate={quote(ctx.mandate_id)}&role={quote(ctx.role_id)}"
    )
    if ctx.client_id:
        ask_qs += f"&client={quote(ctx.client_id)}"
    research_qs = f"context=portfolio&portfolio={quote(ctx.portfolio_id)}&rw=1"
    if ctx.client_id:
        research_qs += f"&client={quote(ctx.client_id)}"

    return InstitutionalPortfolioWorkspace(
        workspace_id=ctx.workspace_id,
        portfolio_id=ctx.portfolio_id,
        mandate=ctx.mandate_id,
        members=members,
        permissions=ctx.permissions,
        linked_publications=tuple(linked_publications or ()),
        client_id=ctx.client_id,
        role_id=ctx.role_id,
        policy_profile=ctx.policy_profile,
        execution_context=ctx,
        ask_deep_link=f"/agi/ask?{ask_qs}",
        research_deep_link=f"/agi/research?{research_qs}",
        diagnostics={
            "resolved_at": now_iso(),
            "owns_intelligence": False,
            "intelligence_is_global": True,
            "client_name": client.client_name if client else "",
            "platform_engine_version": PLATFORM_ENGINE_VERSION,
        },
    )


def context_from_payload(payload: Optional[dict[str, Any]] = None) -> InstitutionalExecutionContext:
    """Parse explicit execution context from request payload (never implicit globals)."""
    body = dict(payload or {})
    nested = body.get("execution_context") or body.get("context") or {}
    if not isinstance(nested, dict):
        nested = {}
    portfolio_id = str(
        nested.get("portfolio_id")
        or body.get("portfolio_id")
        or body.get("portfolio")
        or "agi-core-equity"
    )
    return build_execution_context(
        portfolio_id=portfolio_id,
        client_id=str(nested.get("client_id") or body.get("client_id") or body.get("client") or ""),
        mandate_id=str(nested.get("mandate_id") or body.get("mandate_id") or body.get("mandate") or ""),
        role_id=str(nested.get("role_id") or body.get("role_id") or body.get("role") or "analyst"),
        user_id=str(nested.get("user_id") or body.get("user_id") or body.get("user") or ""),
    )
