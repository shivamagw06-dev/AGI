"""Institutional seed series for valuation multiples.

Labeled institutional_seed — not live Yahoo history.
Used when PIL packs lack PE / index series so producers can still
emit validated packs with transparent provenance.
"""

from __future__ import annotations

from typing import Any

# Approximate FY year-end trailing PE panels (institutional seed).
# Provenance: institutional_seed / Phase 2 Historical Intelligence.
IT_PE_SERIES: dict[str, dict[str, float]] = {
    "INFY": {
        "FY17": 16.5,
        "FY18": 17.8,
        "FY19": 20.2,
        "FY20": 18.5,
        "FY21": 28.4,
        "FY22": 32.1,
        "FY23": 24.8,
        "FY24": 23.2,
        "FY25": 25.1,
        "FY26": 26.4,
    },
    "TCS": {
        "FY17": 18.2,
        "FY18": 19.5,
        "FY19": 22.0,
        "FY20": 21.0,
        "FY21": 33.5,
        "FY22": 35.0,
        "FY23": 28.0,
        "FY24": 27.2,
        "FY25": 28.5,
        "FY26": 29.0,
    },
    "HCLTECH": {
        "FY17": 14.5,
        "FY18": 15.2,
        "FY19": 16.8,
        "FY20": 15.0,
        "FY21": 22.0,
        "FY22": 24.5,
        "FY23": 20.0,
        "FY24": 21.5,
        "FY25": 22.8,
        "FY26": 23.5,
    },
    "WIPRO": {
        "FY17": 15.0,
        "FY18": 16.2,
        "FY19": 17.5,
        "FY20": 14.8,
        "FY21": 26.0,
        "FY22": 24.0,
        "FY23": 18.5,
        "FY24": 19.0,
        "FY25": 20.5,
        "FY26": 21.0,
    },
    "TECHM": {
        "FY17": 13.5,
        "FY18": 14.8,
        "FY19": 16.0,
        "FY20": 13.2,
        "FY21": 25.5,
        "FY22": 23.0,
        "FY23": 17.0,
        "FY24": 18.5,
        "FY25": 20.0,
        "FY26": 21.5,
    },
}

# Nifty IT index trailing PE history (sector/index valuation).
NIFTYIT_PE_SERIES: dict[str, float] = {
    "FY17": 15.8,
    "FY18": 17.0,
    "FY19": 19.5,
    "FY20": 17.2,
    "FY21": 30.0,
    "FY22": 31.5,
    "FY23": 24.0,
    "FY24": 25.5,
    "FY25": 28.0,
    "FY26": 29.5,
}

BANK_PE_SERIES: dict[str, dict[str, float]] = {
    "HDFCBANK": {
        "FY17": 22.0,
        "FY18": 24.5,
        "FY19": 26.0,
        "FY20": 20.0,
        "FY21": 28.0,
        "FY22": 22.5,
        "FY23": 19.0,
        "FY24": 18.5,
        "FY25": 19.5,
        "FY26": 20.5,
    },
    "ICICIBANK": {
        "FY17": 18.0,
        "FY18": 20.0,
        "FY19": 22.0,
        "FY20": 16.0,
        "FY21": 24.0,
        "FY22": 20.0,
        "FY23": 17.5,
        "FY24": 18.0,
        "FY25": 19.0,
        "FY26": 19.8,
    },
    "AXISBANK": {
        "FY22": 16.0,
        "FY23": 14.5,
        "FY24": 13.5,
        "FY25": 14.0,
        "FY26": 14.8,
    },
    "KOTAKBANK": {
        "FY22": 28.0,
        "FY23": 24.0,
        "FY24": 22.0,
        "FY25": 21.0,
        "FY26": 22.5,
    },
    "SBIN": {
        "FY22": 12.0,
        "FY23": 10.5,
        "FY24": 9.5,
        "FY25": 10.0,
        "FY26": 10.8,
    },
}

# Map index / sector aliases → peer universe pack + subject series key.
SECTOR_ENTITY_MAP: dict[str, dict[str, Any]] = {
    "NIFTYIT": {
        "sector": "it_services",
        "pack_id": "it_services_v1",
        "peer_universe": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
        "pe_series": NIFTYIT_PE_SERIES,
        "entity_type": "Index",
        "display_name": "Nifty IT",
    },
    "NIFTYBANK": {
        "sector": "banks",
        "pack_id": "banks_india_v1",
        "peer_universe": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN"],
        "pe_series": None,  # transparent insufficient until seeded
        "entity_type": "Index",
        "display_name": "Nifty Bank",
    },
}

# Historical EV/EBITDA, PB, ROE seeds for INFY (business/accounting producers).
INFY_EXTRA: dict[str, dict[str, float]] = {
    "EV_EBITDA": {
        "FY22": 18.0,
        "FY23": 14.5,
        "FY24": 13.8,
        "FY25": 14.2,
        "FY26": 15.0,
    },
    "PB": {
        "FY22": 7.5,
        "FY23": 6.2,
        "FY24": 5.8,
        "FY25": 6.0,
        "FY26": 6.4,
    },
    "ROE": {
        "FY22": 29.0,
        "FY23": 30.5,
        "FY24": 29.0,
        "FY25": 30.0,
        "FY26": 31.0,
    },
    "ROIC": {
        "FY22": 35.0,
        "FY23": 36.0,
        "FY24": 34.0,
        "FY25": 35.0,
        "FY26": 36.0,
    },
    "Revenue_Growth": {
        "FY22": 21.0,
        "FY23": 15.0,
        "FY24": 2.0,
        "FY25": 4.0,
        "FY26": 5.0,
    },
    "EBITDA_Margin": {
        "FY22": 25.0,
        "FY23": 23.0,
        "FY24": 22.5,
        "FY25": 23.0,
        "FY26": 23.5,
    },
    "Net_Margin": {
        "FY22": 19.0,
        "FY23": 18.0,
        "FY24": 17.5,
        "FY25": 18.0,
        "FY26": 18.2,
    },
    "FCF_Margin": {
        "FY22": 18.0,
        "FY23": 19.0,
        "FY24": 20.0,
        "FY25": 22.0,
        "FY26": 24.0,
    },
    "Cash_Conversion": {
        "FY22": 90.0,
        "FY23": 92.0,
        "FY24": 95.0,
        "FY25": 96.0,
        "FY26": 95.0,
    },
    "Debt": {
        "FY22": 0.05,
        "FY23": 0.04,
        "FY24": 0.03,
        "FY25": 0.02,
        "FY26": 0.02,
    },
}


def pe_series_for(entity_id: str) -> dict[str, float] | None:
    eid = str(entity_id or "").upper()
    if eid in IT_PE_SERIES:
        return dict(IT_PE_SERIES[eid])
    if eid in BANK_PE_SERIES:
        return dict(BANK_PE_SERIES[eid])
    sector = SECTOR_ENTITY_MAP.get(eid)
    if sector and sector.get("pe_series"):
        return dict(sector["pe_series"])
    return None


def sector_meta(entity_id: str) -> dict[str, Any] | None:
    return SECTOR_ENTITY_MAP.get(str(entity_id or "").upper())
