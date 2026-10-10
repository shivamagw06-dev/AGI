"""Configuration-driven source definitions — no hardcoded company-specific connector logic."""

from __future__ import annotations

from typing import Any


# Cadence priorities: lower number = higher priority
DEFAULT_SCHEDULE: list[dict[str, Any]] = [
    {"job_id": "job_company_ir_daily", "connector_id": "company_ir", "cadence": "daily", "priority": 20},
    {"job_id": "job_nse_hourly", "connector_id": "nse", "cadence": "hourly", "priority": 10},
    {"job_id": "job_bse_hourly", "connector_id": "bse", "cadence": "hourly", "priority": 10},
    {"job_id": "job_rbi_daily", "connector_id": "rbi", "cadence": "daily", "priority": 30},
    {"job_id": "job_sebi_daily", "connector_id": "sebi", "cadence": "daily", "priority": 30},
    {"job_id": "job_mof_daily", "connector_id": "mof", "cadence": "daily", "priority": 40},
    {"job_id": "job_mospi_event", "connector_id": "mospi", "cadence": "event", "priority": 15},
    {"job_id": "job_fred_daily", "connector_id": "fred", "cadence": "daily", "priority": 35},
    {"job_id": "job_imf_daily", "connector_id": "imf", "cadence": "daily", "priority": 45},
    {"job_id": "job_worldbank_daily", "connector_id": "worldbank", "cadence": "daily", "priority": 45},
    {"job_id": "job_pib_hourly", "connector_id": "pib", "cadence": "hourly", "priority": 25},
    {"job_id": "job_earnings_season", "connector_id": "company_ir", "cadence": "earnings_hourly", "priority": 5},
]


CONNECTOR_CONFIGS: dict[str, dict[str, Any]] = {
    "company_ir": {
        "doc_types": ["annual_report", "quarterly_result", "investor_presentation", "earnings_transcript", "esg_report", "press_release"],
        "base_path_template": "{ir_url}",
    },
    "nse": {
        "base_url": "https://www.nseindia.com",
        "streams": ["announcements", "corporate_actions", "shareholding", "board_meetings", "financial_filings"],
    },
    "bse": {
        "base_url": "https://www.bseindia.com",
        "streams": ["announcements", "corporate_actions", "shareholding", "board_meetings", "financial_filings"],
    },
    "rbi": {
        "base_url": "https://www.rbi.org.in",
        "streams": ["monetary_policy", "circulars", "macro_data", "banking_statistics"],
    },
    "sebi": {
        "base_url": "https://www.sebi.gov.in",
        "streams": ["circulars", "consultation_papers", "regulations"],
    },
    "mof": {
        "base_url": "https://www.finmin.nic.in",
        "streams": ["budget", "notifications"],
    },
    "mospi": {
        "base_url": "https://www.mospi.gov.in",
        "streams": ["cpi", "wpi", "gdp", "iip"],
    },
    "fred": {
        "base_url": "https://api.stlouisfed.org/fred",
        "series": ["DFF", "DGS10", "UNRATE", "CPIAUCSL"],
    },
    "imf": {
        "base_url": "https://www.imf.org",
        "streams": ["weo", "country_forecasts"],
    },
    "worldbank": {
        "base_url": "https://api.worldbank.org/v2",
        "streams": ["development_indicators"],
    },
    "pib": {
        "base_url": "https://www.pib.gov.in",
        "streams": ["government_announcements"],
    },
}


# Designed for AOI v2+ — registered as optional stubs, not executed in v1 runs.
OPTIONAL_CONNECTORS: list[dict[str, str]] = [
    {"connector_id": "openstreetmap", "name": "OpenStreetMap"},
    {"connector_id": "weather", "name": "Weather"},
    {"connector_id": "satellite", "name": "Satellite"},
    {"connector_id": "ais_shipping", "name": "AIS Shipping"},
    {"connector_id": "commodity_apis", "name": "Commodity APIs"},
    {"connector_id": "energy", "name": "Energy"},
    {"connector_id": "carbon", "name": "Carbon"},
    {"connector_id": "port_activity", "name": "Port Activity"},
]


EXPECTED_DOC_TYPES_PER_COMPANY: list[str] = [
    "annual_report",
    "quarterly_result",
    "investor_presentation",
    "earnings_transcript",
    "esg_report",
    "shareholding",
]
