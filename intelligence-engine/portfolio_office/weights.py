"""Weight / cash calculations — arithmetic on stated market values only."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def apply_weights(portfolio: Mapping[str, Any]) -> dict[str, Any]:
    """
    Compute holding weights and cash weight from current_market_value + cash balance.
    Does not fetch prices or invent valuations — uses provided market values only.
    """
    pf = deepcopy(dict(portfolio))
    holdings = list(pf.get("holdings") or [])
    cash = dict(pf.get("cash") or {})
    equity_mv = sum(float(h.get("current_market_value") or 0.0) for h in holdings)
    cash_bal = float(cash.get("balance") or 0.0)
    total = equity_mv + cash_bal
    if total <= 0:
        for h in holdings:
            h["weight"] = 0.0
        cash["weight"] = 0.0
        pf["holdings"] = holdings
        pf["cash"] = cash
        pf["totals"] = {
            "equity_market_value": equity_mv,
            "cash_balance": cash_bal,
            "total_market_value": total,
        }
        return pf

    for h in holdings:
        mv = float(h.get("current_market_value") or 0.0)
        h["weight"] = mv / total
    cash["weight"] = cash_bal / total
    pf["holdings"] = holdings
    pf["cash"] = cash
    pf["totals"] = {
        "equity_market_value": equity_mv,
        "cash_balance": cash_bal,
        "total_market_value": total,
    }
    return pf
