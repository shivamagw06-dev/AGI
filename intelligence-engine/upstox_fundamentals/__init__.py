"""Upstox Institutional Fundamentals Integration (UIFI) — Phase 7.4E.

Primary structured fundamentals provider for Indian listed companies.
All products read warehouse only — never Upstox directly.
"""

from upstox_fundamentals.production import (
    company_competitors,
    company_corporate_actions,
    company_profile,
    company_profile_history,
    company_shareholding,
    company_statements,
    coverage,
    failures,
    health,
    ingest_bundle,
)

__all__ = [
    "health",
    "coverage",
    "failures",
    "ingest_bundle",
    "company_profile",
    "company_profile_history",
    "company_statements",
    "company_shareholding",
    "company_competitors",
    "company_corporate_actions",
]
