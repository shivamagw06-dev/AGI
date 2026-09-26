"""Indian FMCG peer pack — Nestlé India vs HUL / Britannia / Dabur / ITC + globals."""

from __future__ import annotations

from typing import Any

from peer_intelligence.schema import MetricSeries, PeerIdentity

PACK_ID = "fmcg_india_v1"
SECTOR = "fmcg"

IDENTITIES = [
    PeerIdentity("NESTLEIND", "Nestlé India", "IN", "fmcg", "packaged_foods", "branded_fmcg", "direct", 30),
    PeerIdentity("HINDUNILVR", "Hindustan Unilever", "IN", "fmcg", "diversified_fmcg", "branded_fmcg", "direct", 70),
    PeerIdentity("BRITANNIA", "Britannia Industries", "IN", "fmcg", "bakery", "branded_fmcg", "direct", 15),
    PeerIdentity("DABUR", "Dabur India", "IN", "fmcg", "ayurveda_fmcg", "branded_fmcg", "direct", 10),
    PeerIdentity("ITC", "ITC Limited", "IN", "fmcg", "cigarettes_fmcg", "conglomerate_fmcg", "sector_leader", 70),
    PeerIdentity("NESN", "Nestlé SA", "CH", "fmcg", "global_foods", "branded_fmcg", "global_leader", 280),
    PeerIdentity("UL", "Unilever", "GB", "fmcg", "global_fmcg", "branded_fmcg", "global_leader", 140),
    PeerIdentity("PG", "Procter & Gamble", "US", "fmcg", "global_fmcg", "branded_fmcg", "global_leader", 380),
    PeerIdentity("KO", "Coca-Cola", "US", "fmcg", "beverages", "branded_fmcg", "global_leader", 280),
    PeerIdentity("MDLZ", "Mondelez", "US", "fmcg", "snacks", "branded_fmcg", "global_leader", 90),
]


def _s(metric: str, entity: str, unit: str, points: dict[str, float], source: str = "seed_panel") -> MetricSeries:
    return MetricSeries(metric, entity, unit, points, source, "seed_panel")


def series() -> list[MetricSeries]:
    return [
        _s("Operating_Margin", "NESTLEIND", "%", {"FY22": 22.0, "FY23": 22.5, "FY24": 23.0, "FY25": 23.2, "FY26": 23.5}),
        _s("Operating_Margin", "HINDUNILVR", "%", {"FY22": 23.0, "FY23": 22.5, "FY24": 22.0, "FY25": 22.2, "FY26": 22.0}),
        _s("Operating_Margin", "BRITANNIA", "%", {"FY22": 16.0, "FY23": 17.0, "FY24": 17.5, "FY25": 18.0, "FY26": 18.2}),
        _s("Operating_Margin", "DABUR", "%", {"FY22": 18.0, "FY23": 17.5, "FY24": 17.0, "FY25": 16.5, "FY26": 16.8}),
        _s("Operating_Margin", "ITC", "%", {"FY22": 32.0, "FY23": 33.0, "FY24": 33.5, "FY25": 34.0, "FY26": 34.2}),
        _s("Gross_Margin", "NESTLEIND", "%", {"FY22": 56.0, "FY23": 55.5, "FY24": 56.5, "FY25": 57.0, "FY26": 57.2}),
        _s("Gross_Margin", "HINDUNILVR", "%", {"FY22": 52.0, "FY23": 51.5, "FY24": 51.0, "FY25": 51.5, "FY26": 51.8}),
        _s("Gross_Margin", "BRITANNIA", "%", {"FY22": 40.0, "FY23": 41.0, "FY24": 41.5, "FY25": 42.0, "FY26": 42.2}),
        _s("Gross_Margin", "DABUR", "%", {"FY22": 48.0, "FY23": 47.5, "FY24": 47.0, "FY25": 46.5, "FY26": 47.0}),
        _s("Gross_Margin", "ITC", "%", {"FY22": 58.0, "FY23": 58.5, "FY24": 59.0, "FY25": 59.5, "FY26": 59.8}),
        _s("ROIC", "NESTLEIND", "%", {"FY22": 80.0, "FY23": 85.0, "FY24": 90.0, "FY25": 92.0, "FY26": 95.0}),
        _s("ROIC", "HINDUNILVR", "%", {"FY22": 70.0, "FY23": 72.0, "FY24": 74.0, "FY25": 75.0, "FY26": 76.0}),
        _s("ROIC", "BRITANNIA", "%", {"FY22": 45.0, "FY23": 48.0, "FY24": 50.0, "FY25": 52.0, "FY26": 53.0}),
        _s("ROIC", "DABUR", "%", {"FY22": 35.0, "FY23": 34.0, "FY24": 33.0, "FY25": 32.0, "FY26": 33.0}),
        _s("ROIC", "ITC", "%", {"FY22": 28.0, "FY23": 30.0, "FY24": 32.0, "FY25": 33.0, "FY26": 34.0}),
        _s("Revenue_Growth", "NESTLEIND", "%", {"FY22": 10.0, "FY23": 14.0, "FY24": 12.0, "FY25": 11.0, "FY26": 13.0, "Q1FY27": 25.4}),
        _s("Revenue_Growth", "HINDUNILVR", "%", {"FY22": 11.0, "FY23": 10.0, "FY24": 6.0, "FY25": 5.0, "FY26": 4.0}),
        _s("Revenue_Growth", "BRITANNIA", "%", {"FY22": 9.0, "FY23": 12.0, "FY24": 8.0, "FY25": 7.0, "FY26": 8.0}),
        _s("Revenue_Growth", "DABUR", "%", {"FY22": 8.0, "FY23": 6.0, "FY24": 5.0, "FY25": 4.0, "FY26": 5.0}),
        _s("Revenue_Growth", "ITC", "%", {"FY22": 14.0, "FY23": 12.0, "FY24": 6.0, "FY25": 8.0, "FY26": 9.0}),
        _s("PE", "NESTLEIND", "x", {"FY22": 75.0, "FY23": 72.0, "FY24": 70.0, "FY25": 68.0, "FY26": 72.0}),
        _s("PE", "HINDUNILVR", "x", {"FY22": 65.0, "FY23": 62.0, "FY24": 58.0, "FY25": 55.0, "FY26": 56.0}),
        _s("PE", "BRITANNIA", "x", {"FY22": 50.0, "FY23": 48.0, "FY24": 52.0, "FY25": 55.0, "FY26": 58.0}),
        _s("PE", "DABUR", "x", {"FY22": 55.0, "FY23": 50.0, "FY24": 48.0, "FY25": 45.0, "FY26": 46.0}),
        _s("PE", "ITC", "x", {"FY22": 20.0, "FY23": 22.0, "FY24": 25.0, "FY25": 26.0, "FY26": 27.0}),
    ]


def pack() -> dict[str, Any]:
    return {
        "pack_id": PACK_ID,
        "sector": SECTOR,
        "identities": [i.to_dict() for i in IDENTITIES],
        "series": [s.to_dict() for s in series()],
        "direct_universe": ["NESTLEIND", "HINDUNILVR", "BRITANNIA", "DABUR", "ITC"],
        "global_universe": ["NESN", "UL", "PG", "KO", "MDLZ"],
        "notes": ["Seed panel — Nestlé Q1FY27 sales growth 25.4% aligned to EIL case #11 filing."],
        "missing": ["volume_vs_value_split", "distribution_reach_panel"],
    }
