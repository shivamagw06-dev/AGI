"""Consumer internet / marketplace peer pack — unit-economics oriented."""

from __future__ import annotations

from typing import Any

from peer_intelligence.schema import MetricSeries, PeerIdentity

PACK_ID = "consumer_internet_v1"
SECTOR = "consumer_internet"

IDENTITIES = [
    PeerIdentity("ETERNAL", "Eternal (Zomato)", "IN", "consumer_internet", "food_delivery", "marketplace", "direct", 25),
    PeerIdentity("SWIGGY", "Swiggy", "IN", "consumer_internet", "food_delivery", "marketplace", "direct", 12),
    PeerIdentity("NYKAA", "Nykaa", "IN", "consumer_internet", "beauty_ecommerce", "marketplace", "direct", 8),
    PeerIdentity("PAYTM", "Paytm", "IN", "consumer_internet", "fintech", "payments_platform", "direct", 6),
    PeerIdentity("UBER", "Uber", "US", "consumer_internet", "mobility_delivery", "marketplace", "global_leader", 140),
    PeerIdentity("DASH", "DoorDash", "US", "consumer_internet", "food_delivery", "marketplace", "global_leader", 55),
    PeerIdentity("MELI", "MercadoLibre", "UY", "consumer_internet", "ecommerce_fintech", "platform", "global_leader", 90),
]


def _s(metric: str, entity: str, unit: str, points: dict[str, float]) -> MetricSeries:
    return MetricSeries(metric, entity, unit, points, "seed_panel", "seed_panel")


def series() -> list[MetricSeries]:
    return [
        _s("Take_Rate", "ETERNAL", "%", {"FY22": 20.0, "FY23": 19.0, "FY24": 18.5, "FY25": 18.0, "FY26": 18.2}),
        _s("Take_Rate", "SWIGGY", "%", {"FY22": 19.0, "FY23": 18.5, "FY24": 18.0, "FY25": 17.5, "FY26": 17.8}),
        _s("Take_Rate", "UBER", "%", {"FY22": 22.0, "FY23": 23.0, "FY24": 24.0, "FY25": 24.5, "FY26": 25.0}),
        _s("Take_Rate", "DASH", "%", {"FY22": 18.0, "FY23": 18.5, "FY24": 19.0, "FY25": 19.5, "FY26": 20.0}),
        _s("Contribution_Margin", "ETERNAL", "%", {"FY22": -2.0, "FY23": 2.0, "FY24": 5.0, "FY25": 7.0, "FY26": 8.0}),
        _s("Contribution_Margin", "SWIGGY", "%", {"FY22": -5.0, "FY23": -1.0, "FY24": 2.0, "FY25": 4.0, "FY26": 5.0}),
        _s("Contribution_Margin", "UBER", "%", {"FY22": 3.0, "FY23": 5.0, "FY24": 7.0, "FY25": 8.0, "FY26": 9.0}),
        _s("Contribution_Margin", "DASH", "%", {"FY22": 4.0, "FY23": 6.0, "FY24": 8.0, "FY25": 9.0, "FY26": 10.0}),
        _s("Retention", "ETERNAL", "%", {"FY22": 55.0, "FY23": 58.0, "FY24": 60.0, "FY25": 62.0, "FY26": 63.0}),
        _s("Retention", "SWIGGY", "%", {"FY22": 52.0, "FY23": 54.0, "FY24": 56.0, "FY25": 57.0, "FY26": 58.0}),
        _s("Retention", "UBER", "%", {"FY22": 60.0, "FY23": 62.0, "FY24": 64.0, "FY25": 65.0, "FY26": 66.0}),
        _s("Retention", "DASH", "%", {"FY22": 58.0, "FY23": 60.0, "FY24": 62.0, "FY25": 63.0, "FY26": 64.0}),
        _s("Order_Density", "ETERNAL", "idx", {"FY22": 100.0, "FY23": 120.0, "FY24": 140.0, "FY25": 155.0, "FY26": 170.0}),
        _s("Order_Density", "SWIGGY", "idx", {"FY22": 95.0, "FY23": 110.0, "FY24": 125.0, "FY25": 140.0, "FY26": 150.0}),
        _s("Unit_Economics", "ETERNAL", "score", {"FY22": 40.0, "FY23": 55.0, "FY24": 65.0, "FY25": 72.0, "FY26": 78.0}),
        _s("Unit_Economics", "SWIGGY", "score", {"FY22": 35.0, "FY23": 45.0, "FY24": 55.0, "FY25": 62.0, "FY26": 68.0}),
        _s("Unit_Economics", "UBER", "score", {"FY22": 60.0, "FY23": 70.0, "FY24": 78.0, "FY25": 82.0, "FY26": 85.0}),
        _s("Unit_Economics", "DASH", "score", {"FY22": 55.0, "FY23": 65.0, "FY24": 75.0, "FY25": 80.0, "FY26": 84.0}),
    ]


def pack() -> dict[str, Any]:
    return {
        "pack_id": PACK_ID,
        "sector": SECTOR,
        "identities": [i.to_dict() for i in IDENTITIES],
        "series": [s.to_dict() for s in series()],
        "direct_universe": ["ETERNAL", "SWIGGY", "NYKAA", "PAYTM"],
        "global_universe": ["UBER", "DASH", "MELI"],
        "notes": ["Seed panel for marketplace unit-economics comparisons."],
        "missing": ["CAC_LTV_full_panel", "GOV_vs_revenue_bridge"],
    }
