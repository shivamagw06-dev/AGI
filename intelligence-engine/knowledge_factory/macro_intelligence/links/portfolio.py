"""Portfolio macro exposure knowledge objects (no portfolio reasoning changes)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.links.company import COMPANY_SECTOR, company_macro_link
from knowledge_factory.macro_intelligence.producers.regime import classify_current
from knowledge_factory.macro_intelligence.schema import IMI_VERSION


def _map_macro_bucket(macro: str) -> str | None:
    m = macro.lower()
    if m in {"interest_rates", "yield_curve", "government_bond_yields"}:
        return "interest_rates"
    if m == "inflation":
        return "inflation"
    if m in {"usd_inr", "dxy", "usd", "eur", "jpy"}:
        return "fx"
    if m in {"oil", "natural_gas", "coal", "copper", "steel", "gold", "silver", "agriculture"}:
        return "commodity"
    if m in {"liquidity", "money_supply", "credit_growth"}:
        return "liquidity"
    if m in {"gdp", "global_growth", "us_growth", "china_growth", "europe_growth", "pmi"}:
        return "gdp"
    return None


def portfolio_macro_exposure(symbols: list[str] | None = None) -> dict[str, Any]:
    if symbols is None:
        try:
            from knowledge_factory.nifty500_universe import NIFTY_500

            symbols = list(NIFTY_500)
        except Exception:
            symbols = list(COMPANY_SECTOR.keys())
    buckets = {
        k: {"net_direction_score": 0.0, "contributors": []}
        for k in ("interest_rates", "inflation", "fx", "commodity", "liquidity", "gdp")
    }
    classified = classify_current()
    for sym in symbols:
        link = company_macro_link(sym)
        for sens in link.get("macro_sensitivity") or []:
            bucket = _map_macro_bucket(str(sens.get("macro") or ""))
            if not bucket:
                continue
            direction = sens.get("direction")
            strength = float(sens.get("strength") or 0.0)
            sign = float(direction) if isinstance(direction, (int, float)) else 0.0
            buckets[bucket]["net_direction_score"] = round(
                buckets[bucket]["net_direction_score"] + sign * strength, 4
            )
            buckets[bucket]["contributors"].append(
                {
                    "symbol": sym.upper(),
                    "macro": sens.get("macro"),
                    "direction": direction,
                    "strength": strength,
                }
            )

    obj = {
        "link_type": "portfolio_macro",
        "portfolio_id": "default_knowledge_universe",
        "symbols": [s.upper() for s in symbols],
        "portfolio_macro_exposure": {
            "interest_rate_exposure": buckets["interest_rates"],
            "inflation_exposure": buckets["inflation"],
            "fx_exposure": buckets["fx"],
            "commodity_exposure": buckets["commodity"],
            "liquidity_exposure": buckets["liquidity"],
            "gdp_exposure": buckets["gdp"],
        },
        "portfolio_regime_sensitivity": {
            "active_regimes": list(classified.get("active_regimes") or []),
            "primary_regime": classified.get("primary_regime"),
        },
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
        "no_portfolio_reasoning_changes": True,
        "fabricated": False,
    }
    imi_store.put_links("portfolio", obj)
    return obj
