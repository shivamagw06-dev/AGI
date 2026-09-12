"""Scenario lab — catalogue and objective framing."""

from __future__ import annotations

from typing import Any

from simulation_lab.store.corpus import catalogue_meta, get_scenario, list_scenarios


def list_all_scenarios() -> dict[str, Any]:
    return {
        "scenarios": list_scenarios(),
        "catalogue": catalogue_meta(),
        "primary_question": "What happens if this decision is taken?",
        "rule": "Every simulation records explicit assumptions before outcomes",
    }


def resolve_scenario(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    sid = payload.get("scenario_id") or payload.get("id") or "rebalance_hdfc_plus"
    base = get_scenario(str(sid))
    if not base:
        # Ad-hoc scenario from payload
        base = {
            "id": str(sid),
            "family": payload.get("family") or "ad_hoc",
            "label": payload.get("label") or f"Ad-hoc simulation {sid}",
            "ticker": (payload.get("ticker") or "HDFCBANK").upper(),
            "portfolio_id": payload.get("portfolio_id") or "agib_core_india",
            "objective": payload.get("objective") or "Evaluate proposed institutional decision before capital moves",
            "assumptions": payload.get("assumptions") or {"horizon_months": 12, "evidence": ["committee_proposal"]},
            "supported_simulations": payload.get("supported_simulations") or ["portfolio_rebalance"],
            "ad_hoc": True,
        }
    # Merge caller overrides without dropping recorded assumptions
    overrides = payload.get("assumptions") or {}
    assumptions = {**(base.get("assumptions") or {}), **overrides}
    assumptions["explicitly_recorded"] = True
    return {
        **base,
        "ticker": (payload.get("ticker") or base.get("ticker") or "HDFCBANK").upper(),
        "portfolio_id": payload.get("portfolio_id") or base.get("portfolio_id") or "agib_core_india",
        "assumptions": assumptions,
        "objective": payload.get("objective") or base.get("objective"),
    }
