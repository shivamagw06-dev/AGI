"""Portfolio memory — rebalances, watchlist, attribution, mistakes."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_portfolio, list_portfolios
from institutional_memory.versioning.rules import assert_append_only


def portfolio_history(portfolio_id: str | None = None) -> dict[str, Any]:
    row = get_portfolio(portfolio_id or "agib_core_india")
    if not row:
        return {"found": False, "portfolio_id": portfolio_id, "available": list_portfolios()}
    rebalances = list(row.get("rebalances") or [])
    gate = assert_append_only(rebalances)
    lessons = list(row.get("lessons") or [])
    success = None
    if lessons and lessons[-1].get("success_rate") is not None:
        success = lessons[-1].get("success_rate")
    return {
        "found": True,
        "portfolio_id": row["portfolio_id"],
        "name": row.get("name"),
        "rebalances": rebalances,
        "watchlist_changes": row.get("watchlist_changes") or [],
        "mistakes": row.get("mistakes") or [],
        "lessons": lessons,
        "success_rate": success,
        "repeated_errors": (lessons[-1].get("repeated_errors") if lessons else None),
        "append_only": gate.get("append_only"),
        "rule": "Historical allocation decisions retained for learning — never orders",
        "never_recommendation": True,
    }
