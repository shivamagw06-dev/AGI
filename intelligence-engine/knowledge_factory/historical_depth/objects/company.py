"""Historical Company Knowledge Object compiler."""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.producers.derived import produce_derived, produce_risk_momentum
from knowledge_factory.historical_depth.schema import HD_VERSION
from knowledge_factory.historical_depth.store import filter_pit


def compile_historical_company(entity: str, *, as_of: str | None = None) -> dict[str, Any]:
    e = entity.upper()
    annual = hd_store.get_series("financials_annual", e) or {}
    quarterly = hd_store.get_series("financials_quarterly", e) or {}
    prices = hd_store.get_series("prices", e) or {}
    timeline = hd_store.get_series("timeline", e) or {}
    actions = hd_store.get_series("corporate_actions", e) or {}

    a_recs = list(annual.get("records") or [])
    q_recs = list(quarterly.get("records") or [])
    p_recs = list(prices.get("records") or [])
    t_recs = list(timeline.get("records") or [])
    c_recs = list(actions.get("records") or [])

    if as_of:
        a_recs = filter_pit(a_recs, as_of)
        q_recs = filter_pit(q_recs, as_of)
        p_recs = filter_pit(p_recs, as_of)
        t_recs = filter_pit(t_recs, as_of)
        c_recs = filter_pit(c_recs, as_of)

    derived = produce_derived(e, as_of=as_of)
    risk = produce_risk_momentum(e, as_of=as_of)

    years = len(a_recs)
    current = a_recs[-1] if a_recs else None
    # Historical states keyed by FY
    states = {
        r["period"]: {
            "period": r["period"],
            "period_end": r.get("period_end"),
            "available_from": r.get("available_from"),
            "financials": r.get("payload"),
            "valuation": {
                m: (derived.get("metrics") or {}).get(m, {}).get("points", {}).get(r["period"])
                for m in ("PE", "PB", "EV_EBITDA", "ROIC", "ROE")
            },
        }
        for r in a_recs
    }

    try:
        from knowledge_factory.fixtures.seed import sector_map

        sector = sector_map().get(e, "unknown")
    except Exception:
        sector = "unknown"

    obj = {
        "kind": "historical_company_object",
        "hd_version": HD_VERSION,
        "entity": e,
        "sector": sector,
        "as_of": as_of,
        "current_state": states.get(current["period"]) if current else None,
        "historical_states": states,
        "timeline": t_recs,
        "historical_financials": {
            "annual": {r["period"]: r.get("payload") for r in a_recs},
            "quarterly": {r["period"]: r.get("payload") for r in q_recs},
        },
        "historical_valuation": derived.get("metrics") or {},
        "historical_accounting": {
            "margins": {
                m: (derived.get("metrics") or {}).get(m, {}).get("points")
                for m in ("Gross_Margin", "Net_Margin", "EBIT_Margin", "Cash_Conversion")
            }
        },
        "historical_business_quality": {
            "roic": (derived.get("metrics") or {}).get("ROIC", {}).get("points"),
            "roe": (derived.get("metrics") or {}).get("ROE", {}).get("points"),
        },
        "historical_risk": risk,
        "historical_macro_exposure": {"sector": sector},
        "historical_sector_ranking": {},
        "corporate_actions": c_recs,
        "pe_percentiles": derived.get("pe_percentiles") or {},
        "coverage": {
            "annual_periods": years,
            "quarterly_periods": len(q_recs),
            "price_points": len(p_recs),
            "history_years": years,
            "completeness": round(min(1.0, years / 20.0), 4),
        },
        "point_in_time_integrity": True,
        "insufficient": years == 0,
    }
    hd_store.put_object("company", e if not as_of else f"{e}@{as_of}", obj)
    # Always also store latest entity key when as_of is None
    if as_of is None:
        hd_store.put_object("company", e, obj)
    return obj
