"""MPC-01 quality gates for platform operations."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio import client_registry as creg
from institutional_multi_portfolio import portfolio_registry as preg
from institutional_multi_portfolio.mandate_engine import resolve_mandate
from institutional_multi_portfolio.models import InstitutionalExecutionContext, InstitutionalPortfolioWorkspace
from institutional_multi_portfolio.schema import ROLES


def validate_workspace(workspace: InstitutionalPortfolioWorkspace) -> dict[str, Any]:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    gates["has_mandate"] = bool(workspace.mandate)
    if not workspace.mandate:
        errors.append("workspace lacks a valid mandate")

    m = resolve_mandate(workspace.mandate) if workspace.mandate else None
    gates["policy_profile"] = bool(workspace.policy_profile or (m and m.get("policy_profile")))
    if not gates["policy_profile"]:
        errors.append("portfolio references missing policy profile")

    rec = preg.get_portfolio(workspace.portfolio_id)
    gates["portfolio_exists"] = rec is not None
    if not rec:
        errors.append("orphaned portfolio")

    gates["role_valid"] = workspace.role_id in ROLES or not workspace.role_id
    if workspace.role_id and workspace.role_id not in ROLES:
        errors.append("invalid role assignment")

    gates["lineage"] = bool(workspace.workspace_id and workspace.portfolio_id)
    if not gates["lineage"]:
        errors.append("broken workspace lineage")

    if workspace.client_id:
        client = creg.get_client(workspace.client_id)
        gates["client_exists"] = client is not None
        if not client:
            errors.append("client not found")
    else:
        gates["client_exists"] = True

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "gates": gates,
        "owns_intelligence": False,
    }


def validate_execution_context(ctx: InstitutionalExecutionContext) -> dict[str, Any]:
    errors: list[str] = []
    if not ctx.workspace_id:
        errors.append("missing workspace_id")
    if not ctx.portfolio_id:
        errors.append("missing portfolio_id")
    if not ctx.mandate_id:
        errors.append("workspace lacks a valid mandate")
    if not ctx.policy_profile:
        errors.append("portfolio references missing policy profile")
    if ctx.role_id and ctx.role_id not in ROLES:
        errors.append("invalid role assignment")
    return {"ok": len(errors) == 0, "errors": errors, "immutable": True}


def validate_portfolio_create(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not str(payload.get("portfolio_id") or "").strip():
        errors.append("portfolio_id required")
    mandate = str(payload.get("mandate_id") or payload.get("mandate") or "balanced")
    m = resolve_mandate(mandate)
    if not m.get("policy_profile"):
        errors.append("portfolio references missing policy profile")
    return {"ok": len(errors) == 0, "errors": errors, "mandate": m}
