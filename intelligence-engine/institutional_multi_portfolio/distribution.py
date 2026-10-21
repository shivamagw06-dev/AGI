"""MPC-01 distribution scoping — same publication object, different destinations by scope/permissions."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio import client_registry as creg
from institutional_multi_portfolio.permissions import assert_permission, resolve_permissions
from institutional_multi_portfolio.schema import PUBLICATION_SCOPES

_QUEUE: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    _QUEUE.clear()


def scope_distribution(
    *,
    publication_id: str,
    scope: str = "portfolio",
    portfolio_id: str = "",
    client_id: str = "",
    role_id: str = "portfolio_manager",
    user_id: str = "",
) -> dict[str, Any]:
    sc = str(scope or "portfolio").lower().strip()
    if sc not in PUBLICATION_SCOPES:
        return {"ok": False, "error": f"invalid publication scope: {sc}", "supported": list(PUBLICATION_SCOPES)}

    perms = resolve_permissions(role_id=role_id, user_id=user_id)
    ok, err = assert_permission(perms, "distribute_publications")
    if not ok:
        return {"ok": False, "error": err or "unauthorized publication distribution", "unauthorized": True}

    destinations: list[str] = []
    if sc == "global":
        destinations = ["workspace", "archive"]
    elif sc == "portfolio":
        destinations = [f"portfolio:{portfolio_id or 'unknown'}"]
    elif sc == "client":
        client = creg.get_client(client_id) if client_id else None
        if client:
            destinations = list(client.distribution_targets)
            destinations.append(f"client:{client.client_id}")
        else:
            destinations = [f"client:{client_id or 'unknown'}"]
    elif sc == "committee":
        destinations = ["committee", "workspace"]
    elif sc == "private":
        destinations = [f"private:{user_id or role_id}"]

    record = {
        "ok": True,
        "publication_id": publication_id,
        "scope": sc,
        "destinations": destinations,
        "portfolio_id": portfolio_id,
        "client_id": client_id,
        "same_publication_object": True,
        "intelligence_unchanged": True,
        "permissions_checked_at_platform_layer": True,
    }
    _QUEUE.append(record)
    return record


def publication_queue(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_QUEUE[-limit:]))


def queue_metrics() -> dict[str, Any]:
    return {
        "queued": len(_QUEUE),
        "by_scope": {
            s: sum(1 for r in _QUEUE if r.get("scope") == s) for s in PUBLICATION_SCOPES
        },
    }
