"""Official document catalog — public IR / exchange entrypoints only.

No auth scraping. No broker research. No fabricated content.
"""

from __future__ import annotations

from typing import Any

# Soft catalog of known public document descriptors for Track-4 seed companies.
# Live collectors attempt URL HEAD/GET when urls are absolute; samples used for CI inject.
CATALOG: list[dict[str, Any]] = [
    {
        "company": "INFY",
        "type": "ANNUAL_REPORT",
        "title": "Infosys Annual Report FY24",
        "published_date": "2024-06-15",
        "available_from": "2024-06-15",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.infosys.com/investors/reports-filings.html",
        "sample_file": "infy_annual_report_fy24.txt",
    },
    {
        "company": "INFY",
        "type": "QUARTERLY_REPORT",
        "title": "Infosys Q1 FY25 Financial Results",
        "published_date": "2024-07-18",
        "available_from": "2024-07-18",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.infosys.com/investors/reports-filings/quarterly-results.html",
        "sample_file": "infy_quarterly_q1_fy25.txt",
    },
    {
        "company": "INFY",
        "type": "INVESTOR_PRESENTATION",
        "title": "Infosys Q1 FY25 Investor Presentation",
        "published_date": "2024-07-18",
        "available_from": "2024-07-18",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.infosys.com/investors/reports-filings/quarterly-results.html",
        "sample_file": "infy_presentation_q1_fy25.txt",
    },
    {
        "company": "INFY",
        "type": "CONFERENCE_CALL_TRANSCRIPT",
        "title": "Infosys Q1 FY25 Earnings Call Transcript",
        "published_date": "2024-07-18",
        "available_from": "2024-07-19",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.infosys.com/investors.html",
        "sample_file": "infy_transcript_q1_fy25.txt",
    },
    {
        "company": "INFY",
        "type": "EXCHANGE_FILING",
        "title": "Infosys — Financial Results Exchange Filing",
        "published_date": "2024-07-18",
        "available_from": "2024-07-18",
        "source": "NSE_FILINGS",
        "language": "en",
        "url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "sample_file": "infy_exchange_filing_q1_fy25.txt",
    },
    {
        "company": "TCS",
        "type": "ANNUAL_REPORT",
        "title": "TCS Annual Report FY24",
        "published_date": "2024-06-20",
        "available_from": "2024-06-20",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.tcs.com/investor-relations",
        "sample_file": "tcs_annual_report_fy24.txt",
    },
    {
        "company": "TCS",
        "type": "CORPORATE_GOVERNANCE_REPORT",
        "title": "TCS Corporate Governance Report FY24",
        "published_date": "2024-06-20",
        "available_from": "2024-06-20",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.tcs.com/investor-relations",
        "sample_file": "tcs_governance_fy24.txt",
    },
    {
        "company": "RELIANCE",
        "type": "RISK_DISCLOSURE",
        "title": "Reliance Industries — Risk Factors Extract",
        "published_date": "2024-07-01",
        "available_from": "2024-07-01",
        "source": "COMPANY_IR",
        "language": "en",
        "url": "https://www.ril.com/InvestorRelations.aspx",
        "sample_file": "reliance_risk_disclosure.txt",
    },
]


def catalog_for(ticker: str | None = None) -> list[dict[str, Any]]:
    if not ticker:
        return list(CATALOG)
    t = ticker.upper()
    return [c for c in CATALOG if c["company"] == t]
