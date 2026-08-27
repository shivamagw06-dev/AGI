"""Event propagation — primary, secondary, and third-order effects."""

from __future__ import annotations

from typing import Any

from causal_graph.graph.store import node_for
from causal_graph.transmission.chains import transmission_from

# Named institutional events → shock node + direction
EVENT_CATALOG: dict[str, dict[str, Any]] = {
    "repo_rate_cut": {
        "event": "repo_rate_cut",
        "label": "RBI Repo Rate Cut",
        "shock_node": "repo_rate",
        "shock_direction": -1,
        "magnitude_bps": 50,
        "description": "Policy rate reduction — credit, housing, cement, steel, capital goods chain",
    },
    "repo_rate_hike": {
        "event": "repo_rate_hike",
        "label": "RBI Repo Rate Hike",
        "shock_node": "repo_rate",
        "shock_direction": 1,
        "magnitude_bps": 50,
        "description": "Policy rate increase — NIM/credit trade-off and discount-rate pressure",
    },
    "oil_spike": {
        "event": "oil_spike",
        "label": "Crude Oil Spike",
        "shock_node": "oil",
        "shock_direction": 1,
        "magnitude_pct": 10,
        "description": "Oil ↑ → inflation ↑ → yields ↑ → cost of equity ↑ → bank multiples ↓",
    },
    "oil_decline": {
        "event": "oil_decline",
        "label": "Sustained Crude Oil Decline",
        "shock_node": "oil",
        "shock_direction": -1,
        "magnitude_pct": 10,
        "description": "Oil ↓ eases imported inflation and supports consumer/FMCG margins",
    },
    "rupee_weakness": {
        "event": "rupee_weakness",
        "label": "Rupee Weakness",
        "shock_node": "inr",
        "shock_direction": -1,
        "magnitude_pct": 5,
        "description": "INR ↓ → imported inflation → consumer spending → FMCG margins",
    },
    "rupee_strength": {
        "event": "rupee_strength",
        "label": "Rupee Strength",
        "shock_node": "inr",
        "shock_direction": 1,
        "magnitude_pct": 5,
        "description": "INR ↑ reduces import price pressure; mixed for IT USD translation",
    },
    "us_10y_rise": {
        "event": "us_10y_rise",
        "label": "US 10-Year Yield +100 bps",
        "shock_node": "us_10y",
        "shock_direction": 1,
        "magnitude_bps": 100,
        "description": "Global discount-rate shock into Indian equities via cost of equity and USD",
    },
    "china_slowdown": {
        "event": "china_slowdown",
        "label": "China Demand Slowdown",
        "shock_node": "china_economy",
        "shock_direction": -1,
        "magnitude_pct": 5,
        "description": "China ↓ → copper/steel ↓ → metals margins/earnings ↓",
    },
    "usd_strength": {
        "event": "usd_strength",
        "label": "USD Strength",
        "shock_node": "usd",
        "shock_direction": 1,
        "magnitude_pct": 5,
        "description": "USD ↑ typically lifts IT reported revenue/margins path",
    },
}


def _resolve_event(event: str) -> dict[str, Any] | None:
    key = (event or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "rate_cut": "repo_rate_cut",
        "rbi_cut": "repo_rate_cut",
        "rate_hike": "repo_rate_hike",
        "crude_up": "oil_spike",
        "crude_down": "oil_decline",
        "inr_weak": "rupee_weakness",
        "inr_strong": "rupee_strength",
        "ust_rise": "us_10y_rise",
        "us10y": "us_10y_rise",
        "china": "china_slowdown",
        "dollar": "usd_strength",
    }
    key = aliases.get(key, key)
    return EVENT_CATALOG.get(key)


def propagate_event(event: str, *, max_chains: int = 14) -> dict[str, Any]:
    meta = _resolve_event(event)
    if not meta:
        return {
            "found": False,
            "event": event,
            "available_events": list(EVENT_CATALOG.keys()),
            "primary_effects": [],
            "secondary_effects": [],
            "third_order_effects": [],
        }
    shock = meta["shock_node"]
    chains = transmission_from(shock, max_depth=5, max_chains=max_chains)
    shock_dir = int(meta.get("shock_direction") or 1)
    for c in chains:
        c["shock_aligned_sign"] = shock_dir * int(c.get("net_direction_sign") or 1)
        c["effect_direction"] = "up" if c["shock_aligned_sign"] > 0 else "down"
    primary = [c for c in chains if c.get("order") == 1]
    secondary = [c for c in chains if c.get("order") == 2]
    third = [c for c in chains if (c.get("order") or 0) >= 3]
    affected_sectors = sorted(
        {
            str(n)
            for c in chains
            for n in (c.get("path") or [])
            if str(n).startswith("sector_")
        }
    )
    affected_companies = sorted(
        {
            str(n)
            for c in chains
            for n in (c.get("path") or [])
            if (node_for(str(n)) or {}).get("type") == "company"
        }
    )
    return {
        "found": True,
        "event": meta["event"],
        "label": meta["label"],
        "description": meta["description"],
        "shock_node": shock,
        "shock_node_label": (node_for(shock) or {}).get("label") or shock,
        "shock_direction": shock_dir,
        "magnitude_bps": meta.get("magnitude_bps"),
        "magnitude_pct": meta.get("magnitude_pct"),
        "chains": chains,
        "primary_effects": primary,
        "secondary_effects": secondary,
        "third_order_effects": third,
        "affected_sectors": affected_sectors,
        "affected_companies": affected_companies,
        "propagation_map": {
            "primary": [{"path": c["path_labels"], "direction": c["effect_direction"], "p": c["transmission_probability"]} for c in primary[:8]],
            "secondary": [{"path": c["path_labels"], "direction": c["effect_direction"], "p": c["transmission_probability"]} for c in secondary[:8]],
            "third_order": [{"path": c["path_labels"], "direction": c["effect_direction"], "p": c["transmission_probability"]} for c in third[:8]],
        },
    }


def list_events() -> list[dict[str, Any]]:
    return [
        {"event": v["event"], "label": v["label"], "shock_node": v["shock_node"]}
        for v in EVENT_CATALOG.values()
    ]
