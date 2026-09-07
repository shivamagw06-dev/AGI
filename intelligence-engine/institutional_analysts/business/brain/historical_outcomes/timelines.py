"""Company historical outcome timelines — institutional memory seeds (knowledge assets)."""

from __future__ import annotations

from typing import Any

# Seed timelines for well-known franchises. Soft knowledge — not live data fetches.
COMPANY_TIMELINES: dict[str, list[dict[str, Any]]] = {
    "HDFCBANK": [
        {"year": 2019, "event": "Low-cost deposits", "theme": "funding_advantage", "implication": "Moat strengthening via CASA / liability franchise"},
        {"year": 2020, "event": "COVID", "theme": "stress_test", "implication": "Asset-quality and franchise resilience under shock"},
        {"year": 2021, "event": "Loan growth", "theme": "growth", "implication": "Advantage converted into balance-sheet growth"},
        {"year": 2022, "event": "Merger", "theme": "integration", "implication": "Scale increased; integration and deposit mix became central"},
        {"year": 2023, "event": "CASA decline", "theme": "funding_pressure", "implication": "Historical liability advantage began to soften"},
        {"year": 2024, "event": "Deposit competition", "theme": "funding_pressure", "implication": "Industry competition reduced uniqueness of low-cost funding"},
        {"year": 2025, "event": "NIM pressure", "theme": "margin_pressure", "implication": "Moat still durable, but trajectory no longer strengthening as before"},
    ],
    "HDFC BANK": [
        {"year": 2019, "event": "Low-cost deposits", "theme": "funding_advantage", "implication": "Moat strengthening via CASA / liability franchise"},
        {"year": 2020, "event": "COVID", "theme": "stress_test", "implication": "Asset-quality and franchise resilience under shock"},
        {"year": 2021, "event": "Loan growth", "theme": "growth", "implication": "Advantage converted into balance-sheet growth"},
        {"year": 2022, "event": "Merger", "theme": "integration", "implication": "Scale increased; integration and deposit mix became central"},
        {"year": 2023, "event": "CASA decline", "theme": "funding_pressure", "implication": "Historical liability advantage began to soften"},
        {"year": 2024, "event": "Deposit competition", "theme": "funding_pressure", "implication": "Industry competition reduced uniqueness of low-cost funding"},
        {"year": 2025, "event": "NIM pressure", "theme": "margin_pressure", "implication": "Moat still durable, but trajectory no longer strengthening as before"},
    ],
}

# Illustrative multi-year business quality path (knowledge seed; updated by live opinions over time)
QUALITY_PATHS: dict[str, list[dict[str, Any]]] = {
    "HDFCBANK": [
        {"year": 2018, "business_quality": 78},
        {"year": 2019, "business_quality": 81},
        {"year": 2020, "business_quality": 76},
        {"year": 2021, "business_quality": 84},
        {"year": 2022, "business_quality": 86},
        {"year": 2023, "business_quality": 83},
    ],
}


def timeline_for(company: str, ticker: str | None = None) -> list[dict[str, Any]]:
    keys = []
    if ticker:
        keys.append(str(ticker).upper())
    if company:
        keys.append(str(company).upper())
        keys.append(str(company).upper().replace(" ", ""))
    for key in keys:
        if key in COMPANY_TIMELINES:
            return list(COMPANY_TIMELINES[key])
    return []


def quality_path_for(company: str, ticker: str | None = None) -> list[dict[str, Any]]:
    keys = []
    if ticker:
        keys.append(str(ticker).upper())
    if company:
        keys.append(str(company).upper())
        keys.append(str(company).upper().replace(" ", ""))
    for key in keys:
        if key in QUALITY_PATHS:
            return list(QUALITY_PATHS[key])
    return []
