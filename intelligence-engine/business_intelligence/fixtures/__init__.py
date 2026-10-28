"""Offline official-structure extracts for FIRE-03 deterministic tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from business_intelligence.inventory import documents_from_text

ROOT = Path(__file__).resolve().parent


def sample_ample_bundles() -> list[dict[str, Any]]:
    text = (ROOT / "sample_annual_report.txt").read_text(encoding="utf-8")
    return [
        documents_from_text(
            company="AMPLE",
            doc_type="ANNUAL_REPORT",
            title="AMPLE Annual Report FY2026",
            text=text,
            published_date="2026-06-30",
            reporting_period="FY2026",
            source="COMPANY_IR",
        )
    ]


def sample_infy_style_bundles() -> list[dict[str, Any]]:
    """Lightweight bundles mirroring IDI fixture language for INFY."""
    annual = """INFOSYS LIMITED
Annual Report FY24

Management Discussion
Revenue grew across digital services. Large deal wins remained healthy.
Operating margins were managed through utilisation and cost discipline.

Strategy
Priority themes include generative AI services, cloud transformation, and cost efficiency programmes for clients.

Business Segments
Financial Services, Retail, Communications, Energy & Utilities, Manufacturing, and Hi-Tech remained primary verticals.

Risk Factors
Key risks include client concentration, wage inflation, currency movement, cyber security, and geopolitical disruption.

Capital Allocation
The company continued dividends and buybacks subject to board approval and capital needs.

Guidance
Management outlined demand environment commentary without providing numerical forward guidance in this extract.
"""
    transcript = """INFOSYS LIMITED
Conference Call Transcript — Q1 FY25 Earnings Call

Guidance
CFO: We are maintaining our previously communicated FY25 growth guidance range.

Strategy
CEO: Our AI platforms and industry solutions remain central to client conversations.

Business Segments
Discussion of BFSI and manufacturing deal activity during the quarter.
"""
    return [
        documents_from_text(
            company="INFY",
            doc_type="ANNUAL_REPORT",
            title="INFY ANNUAL_REPORT FY24",
            text=annual,
            published_date="2024-06-15",
            reporting_period="FY2024",
        ),
        documents_from_text(
            company="INFY",
            doc_type="CONFERENCE_CALL_TRANSCRIPT",
            title="INFY CONFERENCE_CALL_TRANSCRIPT Q1 FY25",
            text=transcript,
            published_date="2024-07-19",
            reporting_period="Q1 FY2025",
        ),
    ]
