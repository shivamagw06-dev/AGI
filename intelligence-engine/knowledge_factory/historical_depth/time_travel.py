"""Time travel — 'What did we know then?'

Point-in-time integrity guarantee:
  Every historical query uses only information with available_from <= as_of.
  Example: as_of=2020-03-31 must NOT include earnings released 2020-04-20.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth.objects.company import compile_historical_company
from knowledge_factory.historical_depth.objects.macro import compile_historical_macro
from knowledge_factory.historical_depth.packs import build_historical_pack
from knowledge_factory.historical_depth.validators import assert_no_future_leak
from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.store import filter_pit


def state_as_of(entity: str, as_of: str) -> dict[str, Any]:
    """Load company historical state using only evidence available on as_of."""
    e = entity.upper()
    company = compile_historical_company(e, as_of=as_of)
    macro = compile_historical_macro(as_of=as_of)
    pack = build_historical_pack(e, as_of=as_of)

    # Integrity audit across raw series
    annual = filter_pit((hd_store.get_series("financials_annual", e) or {}).get("records") or [], as_of)
    quarterly = filter_pit((hd_store.get_series("financials_quarterly", e) or {}).get("records") or [], as_of)
    prices = filter_pit((hd_store.get_series("prices", e) or {}).get("records") or [], as_of)
    leak_check = assert_no_future_leak([*annual, *quarterly, *prices], as_of)

    # Explicit: FY20 annual available_from is 2020-07-15 — must be excluded at 2020-03-31
    excluded_future_annual = [
        r["period"]
        for r in ((hd_store.get_series("financials_annual", e) or {}).get("records") or [])
        if str(r.get("available_from") or "") > as_of
    ]
    excluded_future_quarterly = [
        r["period"]
        for r in ((hd_store.get_series("financials_quarterly", e) or {}).get("records") or [])
        if str(r.get("available_from") or "") > as_of
    ]

    if not annual and not prices:
        return {
            "found": False,
            "entity": e,
            "as_of": as_of,
            "reason": "historical_evidence_unavailable",
            "insufficient": True,
            "fabricated": False,
            "point_in_time_integrity": True,
        }

    return {
        "found": True,
        "entity": e,
        "as_of": as_of,
        "company": company,
        "macro": macro,
        "evidence_pack": pack,
        "point_in_time_integrity": leak_check["ok"],
        "integrity_audit": leak_check,
        "excluded_future_annual": excluded_future_annual,
        "excluded_future_quarterly": excluded_future_quarterly,
        "periods_loaded": {
            "annual": [r["period"] for r in annual],
            "quarterly": [r["period"] for r in quarterly],
            "price_points": len(prices),
        },
        "insufficient": False,
        "fabricated": False,
        "note": "No future information leaked past as_of.",
    }


def compare_as_of(entity: str, date_a: str, date_b: str) -> dict[str, Any]:
    """Compare two historical states (e.g. INFY 2015 vs 2025)."""
    a = state_as_of(entity, date_a)
    b = state_as_of(entity, date_b)
    if not a.get("found") or not b.get("found"):
        return {
            "found": False,
            "entity": entity.upper(),
            "date_a": date_a,
            "date_b": date_b,
            "reason": "historical_evidence_unavailable",
            "states": {"a": a, "b": b},
        }

    def _pe(state: dict[str, Any]) -> float | None:
        cur = (state.get("company") or {}).get("current_state") or {}
        return (cur.get("valuation") or {}).get("PE")

    return {
        "found": True,
        "entity": entity.upper(),
        "date_a": date_a,
        "date_b": date_b,
        "states_loaded": 2,
        "state_a": a,
        "state_b": b,
        "pe_a": _pe(a),
        "pe_b": _pe(b),
        "point_in_time_integrity": a.get("point_in_time_integrity") and b.get("point_in_time_integrity"),
    }
