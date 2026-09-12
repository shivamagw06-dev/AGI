"""Historical Macro Knowledge Object."""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.schema import HD_VERSION
from knowledge_factory.historical_depth.store import filter_pit


def compile_historical_macro(*, as_of: str | None = None) -> dict[str, Any]:
    records = hd_store.get_macro_history()
    if as_of:
        records = filter_pit(records, as_of)
    regimes = hd_store.get_regimes()
    if as_of:
        regimes = [r for r in regimes if str(r.get("start") or "") <= as_of]

    by_period = {r["period"]: r.get("payload") for r in records}
    obj = {
        "kind": "historical_macro_object",
        "hd_version": HD_VERSION,
        "as_of": as_of,
        "series": by_period,
        "regimes": regimes,
        "links": {
            "companies": "via sector + regime tags",
            "sectors": "via regime.affected_sectors",
            "outcomes": "via regime_id references",
        },
        "fields": ["repo_rate", "cpi", "usd_inr", "oil_brent", "gdp_india_growth", "pmi_india", "credit_growth", "liquidity"],
        "n_periods": len(records),
        "point_in_time_integrity": True,
    }
    key = "GLOBAL" if not as_of else f"GLOBAL@{as_of}"
    hd_store.put_object("macro", key, obj)
    if as_of is None:
        hd_store.put_object("macro", "GLOBAL", obj)
    return obj
