"""MPC-01 diagnostics + Platform Operations Center soft-slice."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_multi_portfolio import client_registry as creg
from institutional_multi_portfolio import distribution as dist_mod
from institutional_multi_portfolio import portfolio_registry as preg
from institutional_multi_portfolio.schema import (
    MPC_VERSION,
    MPC_WORKSTREAM_ID,
    PLATFORM_ENGINE_VERSION,
)


_AUDIT: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    _AUDIT.clear()


def record_audit(kind: str, detail: str, *, actor: str = "", meta: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        from financial_statements_engine.util import now_iso
    except Exception:  # noqa: BLE001
        from datetime import datetime, timezone

        def now_iso() -> str:
            return datetime.now(timezone.utc).isoformat()

    import hashlib

    event = {
        "event_id": f"aud-{hashlib.sha256(f'{kind}|{detail}|{now_iso()}'.encode()).hexdigest()[:10]}",
        "kind": kind,
        "detail": detail,
        "actor": actor,
        "created_at": now_iso(),
        "meta": dict(meta or {}),
    }
    _AUDIT.append(event)
    return event


def recent_audit(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_AUDIT[-limit:]))


def build_diagnostics(workspace: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "workstream_id": MPC_WORKSTREAM_ID,
        "version": MPC_VERSION,
        "platform_engine_version": PLATFORM_ENGINE_VERSION,
        "portfolio_count": len(preg.list_portfolios()),
        "client_count": len(creg.list_clients()),
        "workspace": workspace,
        "owns_intelligence": False,
        "intelligence_is_global": True,
    }


def platform_ops_board(active_workspaces: Sequence[dict[str, Any]]) -> dict[str, Any]:
    q = dist_mod.queue_metrics()
    return {
        "active_workspaces": len(active_workspaces),
        "portfolio_count": len(preg.list_portfolios()),
        "client_count": len(creg.list_clients()),
        "publication_queue": q.get("queued") or 0,
        "permission_changes": sum(1 for a in _AUDIT if a.get("kind") == "permission_grant"),
        "workspace_health": "ok" if active_workspaces or preg.list_portfolios() else "empty",
        "distribution_status": q,
        "audit_events": len(_AUDIT),
        "recent_audit": recent_audit(6),
        "owns_intelligence": False,
        "intelligence_is_global": True,
    }
