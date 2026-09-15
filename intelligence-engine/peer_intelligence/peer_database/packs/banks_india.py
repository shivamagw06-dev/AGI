"""Indian private/public bank peer pack — seed panel for PIL V1.

Latest-point CASA/NIM/CET1 for HDFC aligned to Q1FY27 filings used in EIL case #11.
Multi-year series are seed_panel (illustrative institutional priors) until filings automation.
"""

from __future__ import annotations

from typing import Any

from peer_intelligence.schema import MetricSeries, PeerIdentity

PACK_ID = "banks_india_v1"
SECTOR = "banks"

IDENTITIES = [
    PeerIdentity("HDFCBANK", "HDFC Bank", "IN", "banks", "private_bank", "universal_bank", "direct", 170),
    PeerIdentity("ICICIBANK", "ICICI Bank", "IN", "banks", "private_bank", "universal_bank", "direct", 110),
    PeerIdentity("AXISBANK", "Axis Bank", "IN", "banks", "private_bank", "universal_bank", "direct", 45),
    PeerIdentity("KOTAKBANK", "Kotak Mahindra Bank", "IN", "banks", "private_bank", "universal_bank", "direct", 45),
    PeerIdentity("SBIN", "State Bank of India", "IN", "banks", "psu_bank", "universal_bank", "sector_leader", 80),
    PeerIdentity("JPM", "JPMorgan Chase", "US", "banks", "global_bank", "universal_bank", "global_leader", 600),
    PeerIdentity("DBS", "DBS Group", "SG", "banks", "regional_bank", "universal_bank", "regional_leader", 90),
    PeerIdentity("BAC", "Bank of America", "US", "banks", "global_bank", "universal_bank", "global_leader", 320),
    PeerIdentity("WFC", "Wells Fargo", "US", "banks", "global_bank", "universal_bank", "global_leader", 220),
    PeerIdentity("HSBC", "HSBC Holdings", "GB", "banks", "global_bank", "universal_bank", "global_leader", 180),
]


def _series(metric: str, entity: str, unit: str, points: dict[str, float], source: str, data_class: str = "seed_panel") -> MetricSeries:
    return MetricSeries(metric, entity, unit, points, source, data_class)


def series() -> list[MetricSeries]:
    return [
        # CASA % — trajectory narrative: HDFC softens vs ICICI more stable
        _series("CASA", "HDFCBANK", "%", {"FY22": 48.0, "FY23": 44.0, "FY24": 38.0, "FY25": 35.0, "FY26": 33.5, "Q1FY27": 32.3}, "HDFC filings + seed_panel; Q1FY27 press release", "mixed"),
        _series("CASA", "ICICIBANK", "%", {"FY22": 45.0, "FY23": 45.5, "FY24": 45.0, "FY25": 44.5, "FY26": 44.0, "Q1FY27": 43.8}, "seed_panel — peer filings pending automation"),
        _series("CASA", "AXISBANK", "%", {"FY22": 45.0, "FY23": 44.0, "FY24": 43.0, "FY25": 42.0, "FY26": 41.0, "Q1FY27": 40.5}, "seed_panel"),
        _series("CASA", "KOTAKBANK", "%", {"FY22": 53.0, "FY23": 52.0, "FY24": 50.0, "FY25": 47.0, "FY26": 45.0, "Q1FY27": 44.0}, "seed_panel"),
        _series("CASA", "SBIN", "%", {"FY22": 45.0, "FY23": 44.0, "FY24": 42.0, "FY25": 41.0, "FY26": 40.0, "Q1FY27": 39.5}, "seed_panel"),
        # NIM %
        _series("NIM", "HDFCBANK", "%", {"FY22": 4.00, "FY23": 4.10, "FY24": 3.60, "FY25": 3.50, "FY26": 3.40, "Q1FY27": 3.26}, "Q1FY27 PR 3.26%; history seed_panel", "mixed"),
        _series("NIM", "ICICIBANK", "%", {"FY22": 3.90, "FY23": 4.10, "FY24": 4.30, "FY25": 4.20, "FY26": 4.10, "Q1FY27": 4.05}, "seed_panel"),
        _series("NIM", "AXISBANK", "%", {"FY22": 3.50, "FY23": 3.80, "FY24": 3.90, "FY25": 3.80, "FY26": 3.73, "Q1FY27": 3.46}, "Q1FY27 3.46% Outlook; history seed_panel", "mixed"),
        _series("NIM", "KOTAKBANK", "%", {"FY22": 4.40, "FY23": 4.60, "FY24": 5.00, "FY25": 4.80, "FY26": 4.60, "Q1FY27": 4.50}, "seed_panel"),
        _series("NIM", "SBIN", "%", {"FY22": 3.20, "FY23": 3.40, "FY24": 3.30, "FY25": 3.20, "FY26": 3.10, "Q1FY27": 3.05}, "seed_panel"),
        # CET1 / capital
        _series("CET1", "HDFCBANK", "%", {"FY22": 17.0, "FY23": 16.5, "FY24": 16.8, "FY25": 17.0, "FY26": 17.5, "Q1FY27": 17.4}, "Q1FY27 presentation 17.4%", "mixed"),
        _series("CET1", "ICICIBANK", "%", {"FY22": 16.0, "FY23": 16.5, "FY24": 16.8, "FY25": 16.9, "FY26": 16.8, "Q1FY27": 16.7}, "seed_panel"),
        _series("CET1", "AXISBANK", "%", {"FY22": 15.0, "FY23": 14.5, "FY24": 14.8, "FY25": 15.0, "FY26": 15.2, "Q1FY27": 15.1}, "seed_panel"),
        _series("CET1", "KOTAKBANK", "%", {"FY22": 20.0, "FY23": 19.5, "FY24": 19.0, "FY25": 18.5, "FY26": 18.0, "Q1FY27": 17.8}, "seed_panel"),
        _series("CET1", "SBIN", "%", {"FY22": 11.0, "FY23": 11.5, "FY24": 12.0, "FY25": 12.2, "FY26": 12.4, "Q1FY27": 12.5}, "seed_panel"),
        # ROE
        _series("ROE", "HDFCBANK", "%", {"FY22": 16.5, "FY23": 17.0, "FY24": 15.0, "FY25": 14.5, "FY26": 14.0, "Q1FY27": 13.8}, "Q1FY27 RoE 13.8%", "mixed"),
        _series("ROE", "ICICIBANK", "%", {"FY22": 14.0, "FY23": 16.0, "FY24": 17.5, "FY25": 18.0, "FY26": 17.5, "Q1FY27": 17.2}, "seed_panel"),
        _series("ROE", "AXISBANK", "%", {"FY22": 12.0, "FY23": 14.0, "FY24": 16.0, "FY25": 16.5, "FY26": 15.5, "Q1FY27": 15.0}, "seed_panel"),
        _series("ROE", "KOTAKBANK", "%", {"FY22": 12.5, "FY23": 13.5, "FY24": 14.0, "FY25": 13.5, "FY26": 13.0, "Q1FY27": 12.8}, "seed_panel"),
        _series("ROE", "SBIN", "%", {"FY22": 12.0, "FY23": 15.0, "FY24": 16.5, "FY25": 17.0, "FY26": 16.0, "Q1FY27": 15.5}, "seed_panel"),
        # GNPA (lower better)
        _series("GNPA", "HDFCBANK", "%", {"FY22": 1.20, "FY23": 1.15, "FY24": 1.25, "FY25": 1.20, "FY26": 1.18, "Q1FY27": 1.17}, "Q1FY27 1.17%", "mixed"),
        _series("GNPA", "ICICIBANK", "%", {"FY22": 3.0, "FY23": 2.5, "FY24": 2.2, "FY25": 2.0, "FY26": 1.9, "Q1FY27": 1.85}, "seed_panel"),
        _series("GNPA", "AXISBANK", "%", {"FY22": 2.8, "FY23": 2.4, "FY24": 1.8, "FY25": 1.5, "FY26": 1.4, "Q1FY27": 1.35}, "seed_panel"),
        _series("GNPA", "KOTAKBANK", "%", {"FY22": 2.2, "FY23": 1.9, "FY24": 1.6, "FY25": 1.5, "FY26": 1.4, "Q1FY27": 1.38}, "seed_panel"),
        _series("GNPA", "SBIN", "%", {"FY22": 4.0, "FY23": 3.2, "FY24": 2.5, "FY25": 2.3, "FY26": 2.1, "Q1FY27": 2.0}, "seed_panel"),
        # Deposit growth
        _series("Deposit_Growth", "HDFCBANK", "%", {"FY22": 17.0, "FY23": 20.0, "FY24": 25.0, "FY25": 16.0, "FY26": 15.0, "Q1FY27": 14.7}, "Q1FY27 deposits +14.7% YoY", "mixed"),
        _series("Deposit_Growth", "ICICIBANK", "%", {"FY22": 15.0, "FY23": 16.0, "FY24": 18.0, "FY25": 15.0, "FY26": 14.0, "Q1FY27": 13.5}, "seed_panel"),
        _series("Deposit_Growth", "AXISBANK", "%", {"FY22": 16.0, "FY23": 14.0, "FY24": 13.0, "FY25": 12.0, "FY26": 11.0, "Q1FY27": 10.5}, "seed_panel"),
        _series("Deposit_Growth", "KOTAKBANK", "%", {"FY22": 12.0, "FY23": 14.0, "FY24": 16.0, "FY25": 14.0, "FY26": 13.0, "Q1FY27": 12.5}, "seed_panel"),
        _series("Deposit_Growth", "SBIN", "%", {"FY22": 10.0, "FY23": 11.0, "FY24": 12.0, "FY25": 11.0, "FY26": 10.0, "Q1FY27": 9.5}, "seed_panel"),
    ]


def pack() -> dict[str, Any]:
    return {
        "pack_id": PACK_ID,
        "sector": SECTOR,
        "identities": [i.to_dict() for i in IDENTITIES],
        "series": [s.to_dict() for s in series()],
        "direct_universe": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN"],
        "global_universe": ["JPM", "DBS", "BAC", "WFC", "HSBC"],
        "notes": [
            "Q1FY27 HDFC points sourced via EIL case #11 filings where noted.",
            "Multi-year peer panels are seed_panel until filings automation closes gaps.",
        ],
        "missing": ["full_CoF_panel", "deposit_share_5y", "global_CASA_comparable"],
    }
