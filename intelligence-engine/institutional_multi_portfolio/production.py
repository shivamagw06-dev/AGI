"""MPC-01 production façades — portfolios / clients / workspaces / permissions / Platform Ops."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio import client_registry as creg
from institutional_multi_portfolio import distribution as dist_mod
from institutional_multi_portfolio import portfolio_registry as preg
from institutional_multi_portfolio.diagnostics import (
    build_diagnostics,
    platform_ops_board,
    record_audit,
    recent_audit,
    reset_for_tests as reset_diag,
)
from institutional_multi_portfolio.flags import flags_dict, is_enabled
from institutional_multi_portfolio.mandate_engine import assign_mandate, list_mandates
from institutional_multi_portfolio.permissions import (
    grant,
    list_roles,
    reset_for_tests as reset_perms,
    resolve_permissions,
)
from institutional_multi_portfolio.schema import (
    MPC_PRODUCT,
    MPC_ROLE,
    MPC_SPEC,
    MPC_VERSION,
    MPC_WORKSTREAM_ID,
    PLATFORM_ENGINE_VERSION,
)
from institutional_multi_portfolio.sharing import collaboration_view, share_research
from institutional_multi_portfolio.validator import (
    validate_execution_context,
    validate_portfolio_create,
    validate_workspace,
)
from institutional_multi_portfolio.workspace_resolver import (
    context_from_payload,
    resolve_workspace,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_WORKSPACES: dict[str, dict[str, Any]] = {}


def reset_for_tests() -> None:
    _WORKSPACES.clear()
    preg.reset_for_tests()
    creg.reset_for_tests()
    reset_perms()
    dist_mod.reset_for_tests()
    reset_diag()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": MPC_WORKSTREAM_ID,
        "product": MPC_PRODUCT,
        "version": MPC_VERSION,
        "role": MPC_ROLE,
        "llm": False,
        "owns_intelligence": False,
        "intelligence_is_global": True,
        "portfolios_are_local": True,
        "execution_context_explicit": True,
        "platform_engine_version": PLATFORM_ENGINE_VERSION,
        "portfolio_count": len(preg.list_portfolios()),
        "client_count": len(creg.list_clients()),
        "roles": list_roles(),
        "mandates": list_mandates(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": MPC_SPEC,
        "brand": "AGI",
        "phase": 5,
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    board = platform_ops_board(list(_WORKSPACES.values()))
    return {
        "status": h.get("status"),
        "workstream_id": MPC_WORKSTREAM_ID,
        "product": MPC_PRODUCT,
        "version": MPC_VERSION,
        "llm": False,
        "platform_operations_center": True,
        "owns_intelligence": False,
        "intelligence_is_global": True,
        **board,
    }


def list_portfolios_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "portfolios": preg.catalog(),
        "count": len(preg.list_portfolios()),
        "intelligence_is_global": True,
    }


def create_portfolio(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": MPC_WORKSTREAM_ID}
    body = dict(payload or {})
    validation = validate_portfolio_create(body)
    if not validation["ok"]:
        return {
            "ok": False,
            "rejected": True,
            "validation_errors": validation["errors"],
            "workstream_id": MPC_WORKSTREAM_ID,
        }
    rec = preg.register_portfolio(
        str(body.get("portfolio_id")),
        name=str(body.get("name") or body.get("portfolio_id")),
        mandate_id=str(body.get("mandate_id") or body.get("mandate") or "balanced"),
        members=body.get("members") or ("analyst@agi",),
        client_ids=body.get("client_ids") or (),
    )
    record_audit("portfolio_create", f"Created {rec.portfolio_id}", actor=str(body.get("user_id") or ""))
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "portfolio": rec.to_dict(),
        "intelligence_unchanged": True,
    }


def list_clients_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "clients": creg.catalog(),
        "count": len(creg.list_clients()),
        "intelligence_is_global": True,
    }


def create_client(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": MPC_WORKSTREAM_ID}
    body = dict(payload or {})
    cid = str(body.get("client_id") or "").strip()
    if not cid:
        return {"ok": False, "rejected": True, "validation_errors": ["client_id required"]}
    client = creg.register_client(
        cid,
        client_name=str(body.get("client_name") or body.get("name") or cid),
        portfolios=body.get("portfolios") or (),
        policy_profile=str(body.get("policy_profile") or "family_office"),
        publication_preferences=body.get("publication_preferences"),
    )
    record_audit("client_create", f"Created {client.client_id}", actor=str(body.get("user_id") or ""))
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "client": client.to_dict(),
        "intelligence_unchanged": True,
    }


def get_workspace(workspace_id: str = "", **kwargs: Any) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": MPC_WORKSTREAM_ID}

    # Allow resolve by portfolio if workspace_id looks like portfolio or empty
    portfolio_id = str(kwargs.get("portfolio_id") or "")
    if workspace_id and workspace_id in _WORKSPACES:
        cached = _WORKSPACES[workspace_id]
        return {
            "ok": True,
            "workstream_id": MPC_WORKSTREAM_ID,
            "workspace": cached,
            "execution_context": cached.get("execution_context"),
        }

    if workspace_id and not portfolio_id and not workspace_id.startswith("ws-"):
        portfolio_id = workspace_id

    ws = resolve_workspace(
        portfolio_id=portfolio_id or "agi-core-equity",
        client_id=str(kwargs.get("client_id") or ""),
        role_id=str(kwargs.get("role_id") or "analyst"),
        user_id=str(kwargs.get("user_id") or ""),
        mandate_id=str(kwargs.get("mandate_id") or ""),
    )
    validation = validate_workspace(ws)
    if not validation["ok"]:
        return {
            "ok": False,
            "rejected": True,
            "validation_errors": validation["errors"],
            "gates": validation["gates"],
            "workspace": ws.to_dict(),
            "workstream_id": MPC_WORKSTREAM_ID,
        }
    stored = ws.to_dict()
    stored["validation"] = validation
    _WORKSPACES[ws.workspace_id] = stored
    record_audit("workspace_resolve", f"Resolved {ws.workspace_id} for {ws.portfolio_id}")
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "workspace": stored,
        "execution_context": stored.get("execution_context"),
        "diagnostics": build_diagnostics(stored),
        "owns_intelligence": False,
    }


def set_permissions(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    user_id = str(body.get("user_id") or "")
    permissions = body.get("permissions") or []
    role_id = str(body.get("role_id") or "")
    if role_id and not permissions:
        permissions = list(resolve_permissions(role_id=role_id))
    result = grant(user_id, permissions)
    if result.get("ok"):
        record_audit(
            "permission_grant",
            f"Granted {permissions} to {user_id}",
            actor=str(body.get("actor") or "administrator"),
            meta={"role_id": role_id},
        )
    result["workstream_id"] = MPC_WORKSTREAM_ID
    result["separate_from_data"] = True
    return result


def distribute_publication(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    result = dist_mod.scope_distribution(
        publication_id=str(body.get("publication_id") or ""),
        scope=str(body.get("scope") or "portfolio"),
        portfolio_id=str(body.get("portfolio_id") or ""),
        client_id=str(body.get("client_id") or ""),
        role_id=str(body.get("role_id") or "portfolio_manager"),
        user_id=str(body.get("user_id") or ""),
    )
    result["workstream_id"] = MPC_WORKSTREAM_ID
    if result.get("ok"):
        record_audit("publication_distribute", f"Scoped {body.get('publication_id')} as {body.get('scope')}")
    return result


def resolve_context(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ctx = context_from_payload(payload)
    validation = validate_execution_context(ctx)
    return {
        "ok": validation["ok"],
        "workstream_id": MPC_WORKSTREAM_ID,
        "execution_context": ctx.to_dict(),
        "validation_errors": validation.get("errors") or [],
        "for_orchestrators": [
            "UAG-01",
            "RW-01",
            "PUB-01",
            "CIO-01",
            "PCE-01",
        ],
        "domain_engines_may_ignore_unused_fields": True,
        "owns_intelligence": False,
    }


def ask_scoped(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Soft-bridge: enrich Ask payload with explicit execution context; UAG still owns orchestration."""
    body = dict(payload or {})
    ctx = context_from_payload(body)
    validation = validate_execution_context(ctx)
    if not validation["ok"]:
        return {
            "ok": False,
            "rejected": True,
            "validation_errors": validation["errors"],
            "workstream_id": MPC_WORKSTREAM_ID,
        }

    ask_body = {
        **body,
        "portfolio_id": ctx.portfolio_id,
        "policy": ctx.policy_profile or body.get("policy") or "family_office",
        "execution_context": ctx.to_dict(),
    }
    # Rewrite bare buy questions into portfolio-scoped form when portfolio present
    q = str(body.get("question") or body.get("query") or body.get("q") or "").strip()
    if q and ctx.portfolio_id and "portfolio" not in q.lower():
        ask_body["question"] = f"{q} (portfolio context: {ctx.portfolio_id}, mandate: {ctx.mandate_id})"
        ask_body["scoped_question"] = True

    try:
        from institutional_orchestrator.production import ask as uag_ask

        result = uag_ask(ask_body)
        result["execution_context"] = ctx.to_dict()
        result["mpc_workstream_id"] = MPC_WORKSTREAM_ID
        result["context_changes_response_not_company_truth"] = True
        return result
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc),
            "execution_context": ctx.to_dict(),
            "workstream_id": MPC_WORKSTREAM_ID,
        }


def platform_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": MPC_WORKSTREAM_ID,
        "portfolios": preg.catalog(),
        "clients": creg.catalog(),
        "mandates": list_mandates(),
        "roles": list_roles(),
        "active_workspaces": list(_WORKSPACES.values()),
        "publication_queue": dist_mod.publication_queue(10),
        "audit": recent_audit(12),
        "collaboration": collaboration_view("agi-core-equity"),
        "owns_intelligence": False,
        "intelligence_is_global": True,
    }


def assign_portfolio_mandate(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    result = assign_mandate(
        str(body.get("portfolio_id") or ""),
        str(body.get("mandate_id") or body.get("mandate") or "balanced"),
    )
    result["workstream_id"] = MPC_WORKSTREAM_ID
    if result.get("ok"):
        record_audit("mandate_assign", f"{body.get('portfolio_id')} → {body.get('mandate_id')}")
    return result


def share(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    result = share_research(
        from_portfolio=str(body.get("from_portfolio") or ""),
        to_portfolio=str(body.get("to_portfolio") or ""),
        object_ref=str(body.get("object_ref") or body.get("ref") or ""),
        role_id=str(body.get("role_id") or "senior_analyst"),
    )
    result["workstream_id"] = MPC_WORKSTREAM_ID
    return result
