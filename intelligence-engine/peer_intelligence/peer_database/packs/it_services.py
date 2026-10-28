"""IT services peer pack — TCS vs Infosys / HCL / Wipro / TechM + globals."""

from __future__ import annotations

from typing import Any

from peer_intelligence.schema import MetricSeries, PeerIdentity

PACK_ID = "it_services_v1"
SECTOR = "it_services"

IDENTITIES = [
    PeerIdentity("TCS", "Tata Consultancy Services", "IN", "it_services", "tier1_it", "it_services", "direct", 180),
    PeerIdentity("INFY", "Infosys", "IN", "it_services", "tier1_it", "it_services", "direct", 80),
    PeerIdentity("HCLTECH", "HCL Technologies", "IN", "it_services", "tier1_it", "it_services", "direct", 50),
    PeerIdentity("WIPRO", "Wipro", "IN", "it_services", "tier1_it", "it_services", "direct", 30),
    PeerIdentity("TECHM", "Tech Mahindra", "IN", "it_services", "tier1_it", "it_services", "direct", 15),
    PeerIdentity("ACN", "Accenture", "US", "it_services", "global_consulting", "it_services", "global_leader", 220),
    PeerIdentity("IBM", "IBM", "US", "it_services", "global_tech", "hybrid_it", "global_leader", 180),
    PeerIdentity("CAP", "Capgemini", "FR", "it_services", "global_consulting", "it_services", "global_leader", 35),
    PeerIdentity("EPAM", "EPAM Systems", "US", "it_services", "digital_engineering", "it_services", "global_leader", 12),
]


def _s(metric: str, entity: str, unit: str, points: dict[str, float]) -> MetricSeries:
    return MetricSeries(metric, entity, unit, points, "seed_panel", "seed_panel")


def series() -> list[MetricSeries]:
    return [
        _s("EBIT_Margin", "TCS", "%", {"FY22": 25.0, "FY23": 24.5, "FY24": 24.0, "FY25": 24.2, "FY26": 24.5}),
        _s("EBIT_Margin", "INFY", "%", {"FY22": 23.0, "FY23": 21.0, "FY24": 20.5, "FY25": 21.0, "FY26": 21.2}),
        _s("EBIT_Margin", "HCLTECH", "%", {"FY22": 19.0, "FY23": 18.5, "FY24": 18.0, "FY25": 18.2, "FY26": 18.5}),
        _s("EBIT_Margin", "WIPRO", "%", {"FY22": 18.0, "FY23": 15.5, "FY24": 15.0, "FY25": 15.5, "FY26": 16.0}),
        _s("EBIT_Margin", "TECHM", "%", {"FY22": 15.0, "FY23": 11.0, "FY24": 9.0, "FY25": 10.0, "FY26": 11.0}),
        _s("Revenue_Growth", "TCS", "%", {"FY22": 17.0, "FY23": 16.0, "FY24": 7.0, "FY25": 5.0, "FY26": 6.0}),
        _s("Revenue_Growth", "INFY", "%", {"FY22": 21.0, "FY23": 15.0, "FY24": 2.0, "FY25": 4.0, "FY26": 5.0}),
        _s("Revenue_Growth", "HCLTECH", "%", {"FY22": 14.0, "FY23": 14.0, "FY24": 8.0, "FY25": 6.0, "FY26": 7.0}),
        _s("Revenue_Growth", "WIPRO", "%", {"FY22": 18.0, "FY23": 12.0, "FY24": -2.0, "FY25": 1.0, "FY26": 3.0}),
        _s("Revenue_Growth", "TECHM", "%", {"FY22": 16.0, "FY23": 14.0, "FY24": -1.0, "FY25": 2.0, "FY26": 4.0}),
        _s("Attrition", "TCS", "%", {"FY22": 17.0, "FY23": 21.0, "FY24": 13.0, "FY25": 12.5, "FY26": 12.0}),
        _s("Attrition", "INFY", "%", {"FY22": 20.0, "FY23": 27.0, "FY24": 14.0, "FY25": 13.0, "FY26": 12.5}),
        _s("Attrition", "HCLTECH", "%", {"FY22": 19.0, "FY23": 22.0, "FY24": 13.5, "FY25": 13.0, "FY26": 12.8}),
        _s("Attrition", "WIPRO", "%", {"FY22": 22.0, "FY23": 23.0, "FY24": 15.0, "FY25": 14.0, "FY26": 13.5}),
        _s("Attrition", "TECHM", "%", {"FY22": 23.0, "FY23": 24.0, "FY24": 16.0, "FY25": 15.0, "FY26": 14.5}),
        _s("ROIC", "TCS", "%", {"FY22": 45.0, "FY23": 48.0, "FY24": 50.0, "FY25": 52.0, "FY26": 53.0}),
        _s("ROIC", "INFY", "%", {"FY22": 35.0, "FY23": 36.0, "FY24": 34.0, "FY25": 35.0, "FY26": 36.0}),
        _s("ROIC", "HCLTECH", "%", {"FY22": 28.0, "FY23": 29.0, "FY24": 28.0, "FY25": 29.0, "FY26": 30.0}),
        _s("ROIC", "WIPRO", "%", {"FY22": 20.0, "FY23": 18.0, "FY24": 16.0, "FY25": 17.0, "FY26": 18.0}),
        _s("ROIC", "TECHM", "%", {"FY22": 22.0, "FY23": 18.0, "FY24": 14.0, "FY25": 15.0, "FY26": 16.0}),
        _s("Cash_Conversion", "TCS", "%", {"FY22": 95.0, "FY23": 98.0, "FY24": 100.0, "FY25": 102.0, "FY26": 100.0}),
        _s("Cash_Conversion", "INFY", "%", {"FY22": 90.0, "FY23": 92.0, "FY24": 95.0, "FY25": 96.0, "FY26": 95.0}),
        _s("Cash_Conversion", "HCLTECH", "%", {"FY22": 85.0, "FY23": 88.0, "FY24": 90.0, "FY25": 91.0, "FY26": 90.0}),
        _s("Cash_Conversion", "WIPRO", "%", {"FY22": 80.0, "FY23": 82.0, "FY24": 85.0, "FY25": 86.0, "FY26": 85.0}),
        _s("Cash_Conversion", "TECHM", "%", {"FY22": 75.0, "FY23": 78.0, "FY24": 80.0, "FY25": 82.0, "FY26": 81.0}),
        # Phase 2 — Historical PE panels (institutional seed → PIL overlay)
        _s("PE", "TCS", "x", {"FY22": 35.0, "FY23": 28.0, "FY24": 27.2, "FY25": 28.5, "FY26": 29.0}),
        _s("PE", "INFY", "x", {"FY22": 32.1, "FY23": 24.8, "FY24": 23.2, "FY25": 25.1, "FY26": 26.4}),
        _s("PE", "HCLTECH", "x", {"FY22": 24.5, "FY23": 20.0, "FY24": 21.5, "FY25": 22.8, "FY26": 23.5}),
        _s("PE", "WIPRO", "x", {"FY22": 24.0, "FY23": 18.5, "FY24": 19.0, "FY25": 20.5, "FY26": 21.0}),
        _s("PE", "TECHM", "x", {"FY22": 23.0, "FY23": 17.0, "FY24": 18.5, "FY25": 20.0, "FY26": 21.5}),
    ]


def pack() -> dict[str, Any]:
    return {
        "pack_id": PACK_ID,
        "sector": SECTOR,
        "identities": [i.to_dict() for i in IDENTITIES],
        "series": [s.to_dict() for s in series()],
        "direct_universe": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
        "global_universe": ["ACN", "IBM", "CAP", "EPAM"],
        "notes": ["Seed panel for comparative IT services quality/margins."],
        "missing": ["utilisation_panel", "large_deal_TCV_panel"],
    }
