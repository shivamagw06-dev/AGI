"""Counterfactual engine — what if the shock had not occurred?"""

from __future__ import annotations

from typing import Any

from causal_graph.propagation.engine import EVENT_CATALOG, propagate_event


def counterfactuals(event: str | None = None, *, ticker: str | None = None) -> dict[str, Any]:
    """Estimate likely alternative outcomes if a named shock were absent/reversed."""
    scenarios: list[dict[str, Any]] = []
    catalog = list(EVENT_CATALOG.keys())
    targets = [event] if event else ["oil_spike", "repo_rate_cut", "rupee_weakness", "us_10y_rise"]
    for ev in targets:
        if not ev:
            continue
        key = str(ev).strip().lower().replace(" ", "_").replace("-", "_")
        base = propagate_event(key)
        if not base.get("found"):
            continue
        # Counterfactual: reverse shock direction narrative
        alt_chains = []
        for c in (base.get("chains") or [])[:6]:
            alt_chains.append(
                {
                    "path": c.get("path_labels"),
                    "observed_direction": c.get("effect_direction"),
                    "counterfactual_direction": "down" if c.get("effect_direction") == "up" else "up",
                    "transmission_probability": c.get("transmission_probability"),
                    "note": "If shock absent/reversed, transmission sign flips along the same evidenced chain",
                }
            )
        scenarios.append(
            {
                "question": f"What if {base.get('label')} had not occurred (or reversed)?",
                "event": base.get("event"),
                "baseline_shock": {
                    "node": base.get("shock_node_label"),
                    "direction": base.get("shock_direction"),
                },
                "likely_alternative_outcomes": alt_chains,
                "affected_sectors": base.get("affected_sectors"),
                "affected_companies": [
                    c for c in (base.get("affected_companies") or []) if (not ticker or c == ticker.upper())
                ],
                "confidence_note": "Counterfactuals inherit edge evidence; they are structured estimates, not forecasts",
            }
        )
    return {
        "count": len(scenarios),
        "scenarios": scenarios,
        "available_events": catalog,
        "ticker_filter": (ticker or "").upper() or None,
    }
