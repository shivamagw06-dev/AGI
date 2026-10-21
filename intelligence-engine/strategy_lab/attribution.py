"""Paper/live attribution and continuous validation evidence."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from institutional_warehouse import store


def attribute(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    security: dict[str, float] = defaultdict(float)
    sector: dict[str, float] = defaultdict(float)
    factor: dict[str, float] = defaultdict(float)
    gross = costs = slippage = 0.0
    for raw in rows:
        row = dict(raw)
        pnl = float(row.get("gross_pnl") or 0.0)
        cost = float(row.get("transaction_cost") or 0.0)
        slip = float(row.get("slippage_cost") or 0.0)
        gross += pnl
        costs += cost
        slippage += slip
        security[str(row.get("symbol") or row.get("company_id") or "UNKNOWN")] += pnl - cost - slip
        sector[str(row.get("sector") or "UNKNOWN")] += pnl - cost - slip
        for name, exposure in (row.get("factor_exposures") or {}).items():
            factor[str(name)] += pnl * float(exposure)
    return {
        "gross_pnl": gross,
        "transaction_costs": costs,
        "slippage_costs": slippage,
        "net_pnl": gross - costs - slippage,
        "security_attribution": dict(security),
        "sector_attribution": dict(sector),
        "factor_attribution": dict(factor),
    }


def persist_daily(
    strategy_id: str,
    as_of: str,
    mode: str,
    result: Mapping[str, Any],
    *,
    actor: str = "system",
) -> dict[str, Any]:
    if mode not in {"PAPER", "LIVE"}:
        raise ValueError("attribution_mode_must_be_paper_or_live")
    rows = []
    for scope in ("security_attribution", "sector_attribution", "factor_attribution"):
        for key, value in (result.get(scope) or {}).items():
            rows.append({
                "strategy_id": strategy_id,
                "as_of": as_of,
                "mode": mode,
                "scope": scope.replace("_attribution", "").upper(),
                "attribution_key": key,
                "pnl": value,
                "gross_pnl": result.get("gross_pnl"),
                "transaction_costs": result.get("transaction_costs"),
                "slippage_costs": result.get("slippage_costs"),
                "net_pnl": result.get("net_pnl"),
            })
    return store.upsert(
        "strategy_live_attribution", rows, source="strategy_attribution", actor=actor,
        reason=f"append_{mode.lower()}_attribution",
    )
