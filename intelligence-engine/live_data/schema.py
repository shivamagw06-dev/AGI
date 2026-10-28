"""LIDI — Live Institutional Data Ingestion schemas."""

from __future__ import annotations

from typing import Any

LIDI_VERSION = "live-institutional-data-ingestion-v1.0.0"
PROGRAMME = "AGIB v3.0 – Live Institutional Data Ingestion"
MODULE_CODE = "LIDI"

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "source_id": "nse_bhavcopy",
        "name": "NSE Bhavcopy",
        "official_source": "NSE India",
        "category": "market_prices",
        "frequency": "daily",
        "priority": 1,
        "purpose": "Daily prices, volumes, returns, liquidity, historical pricing",
    },
    {
        "source_id": "nse_announcements",
        "name": "NSE Corporate Announcements",
        "official_source": "NSE India",
        "category": "corporate_events",
        "frequency": "intraday_poll",
        "priority": 2,
        "purpose": "Corporate events, results, guidance, board meetings, buybacks",
    },
    {
        "source_id": "bse_corporate_actions",
        "name": "BSE Corporate Actions",
        "official_source": "BSE India",
        "category": "corporate_actions",
        "frequency": "daily",
        "priority": 3,
        "purpose": "Splits, bonus, rights, dividends, corporate actions",
    },
    {
        "source_id": "rbi_dbie",
        "name": "RBI DBIE",
        "official_source": "Reserve Bank of India DBIE",
        "category": "macro",
        "frequency": "daily_to_weekly",
        "priority": 4,
        "purpose": "Repo, reverse repo, CRR, SLR, credit, deposits, liquidity, macro",
    },
    {
        "source_id": "company_ir",
        "name": "Company Investor Relations",
        "official_source": "Company IR websites",
        "category": "filings_guidance",
        "frequency": "event_driven",
        "priority": 5,
        "purpose": "Results, presentations, guidance, annual/quarterly reports",
    },
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "governance": True,
    "committees": True,
    "reasoning": True,
    "soft_wire_only": True,
    "never_raw_to_reasoning": True,
    "never_silent_fixture_fallback": True,
    "fixtures_dev_only": True,
}

DEFAULT_RETRY = {"max_attempts": 3, "backoff_seconds": [1, 2, 4]}
