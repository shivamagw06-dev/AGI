"""MPC-01 sharing — cross-team collaboration without duplicating intelligence."""

from __future__ import annotations

from typing import Any

from institutional_multi_portfolio import portfolio_registry as preg
from institutional_multi_portfolio.permissions import has_permission, resolve_permissions


def share_research(
    *,
    from_portfolio: str,
    to_portfolio: str,
    object_ref: str,
    role_id: str = "senior_analyst",
) -> dict[str, Any]:
    """Share a reference to a global intelligence object across portfolios."""
    perms = resolve_permissions(role_id=role_id)
    if not has_permission(perms, "view_research"):
        return {"ok": False, "error": "missing permission: view_research"}
    src = preg.get_portfolio(from_portfolio)
    dst = preg.get_portfolio(to_portfolio)
    if not src or not dst:
        return {"ok": False, "error": "portfolio not found"}
    return {
        "ok": True,
        "shared_ref": object_ref,
        "from_portfolio": from_portfolio,
        "to_portfolio": to_portfolio,
        "mode": "reference",
        "duplicates_intelligence": False,
        "intelligence_is_global": True,
        "note": "Shared as reference to global intelligence object — not copied",
    }


def collaboration_view(portfolio_id: str) -> dict[str, Any]:
    rec = preg.get_portfolio(portfolio_id)
    if not rec:
        return {"ok": False, "error": "portfolio not found"}
    peers = [p.portfolio_id for p in preg.list_portfolios() if p.portfolio_id != portfolio_id]
    return {
        "ok": True,
        "portfolio_id": portfolio_id,
        "members": list(rec.members),
        "peer_portfolios": peers,
        "shared_intelligence": True,
        "local_mandate": rec.mandate_id,
        "local_policy_profile": rec.policy_profile,
    }
