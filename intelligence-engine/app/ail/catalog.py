"""Authoritative company seeds — every claim carries source URL provenance."""

from __future__ import annotations

from typing import Any

COMPANIES: dict[str, dict[str, Any]] = {
    "RELIANCE": {
        "company": "Reliance Industries",
        "aliases": ["reliance", "ril", "reliance industries"],
        "overview": "Diversified conglomerate spanning oil-to-chemicals, digital services (Jio), and retail.",
        "business_model": "Integrated energy value chain plus consumer digital and retail platforms.",
        "segments": ["Oil-to-Chemicals", "Jio Platforms", "Retail", "New Energy"],
        "geographies": ["India", "Global exports"],
        "competitors": ["BHARTIARTL", "ONGC", "IOCL"],
        "industry_position": "India's largest private conglomerate by revenue/market cap cohort.",
        "ir_url": "https://www.ril.com/InvestorRelations/Overview.aspx",
        "annual_url": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "seed_claims": [
            {
                "field": "company_overview",
                "claim": "Reliance Industries is a diversified conglomerate with O2C, digital (Jio), and retail platforms.",
                "source": "Company Investor Relations",
                "url": "https://www.ril.com/InvestorRelations/Overview.aspx",
                "section": "Overview",
                "authority": 10,
                "connector": "company_ir",
            },
            {
                "field": "segments",
                "claim": "Key reporting segments include Oil-to-Chemicals, Jio Platforms, Retail, and New Energy initiatives.",
                "source": "FY Annual / IR Financial Reporting",
                "url": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
                "section": "Segments",
                "page": 1,
                "authority": 10,
                "connector": "company_ir",
            },
            {
                "field": "guidance",
                "claim": "Management continues to emphasise retail/digital scale and new energy capex as multi-year growth vectors.",
                "source": "Investor presentation / conference materials",
                "url": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
                "section": "Strategy",
                "authority": 8,
                "connector": "company_ir",
            },
            {
                "field": "risks",
                "claim": "Material risks include refining/chemical margin cyclicality, regulatory/policy changes, and large capex execution.",
                "source": "Annual report risk factors (IR hub)",
                "url": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
                "section": "Risks",
                "authority": 10,
                "connector": "company_ir",
            },
            {
                "field": "catalysts",
                "claim": "Near-term catalysts: quarterly O2C/Jio/Retail prints, new energy project milestones, and capital allocation updates.",
                "source": "Exchange filings / IR updates",
                "url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
                "section": "Filings",
                "authority": 10,
                "connector": "nse",
            },
        ],
        "timeline_seed": [
            {"year": 2016, "title": "Jio commercial launch era", "category": "strategy"},
            {"year": 2020, "title": "Jio Platforms investment round wave", "category": "m_and_a"},
            {"year": 2023, "title": "New energy / green hydrogen strategy emphasis", "category": "capex"},
            {"year": 2025, "title": "Retail + digital scale narrative continues", "category": "results"},
            {"year": 2026, "title": "Latest IR / filings monitoring window", "category": "monitoring"},
        ],
        "financial_seed": {
            "revenue_inr_cr_p50": 950000.0,
            "ebitda_margin_p50": 0.16,
            "eps_p50": 95.0,
            "net_debt_p50": 120000.0,
            "roe_p50": 0.10,
            "target_multiple_p50": 22.0,
        },
    },
    "TCS": {
        "company": "Tata Consultancy Services",
        "aliases": ["tcs", "tata consultancy"],
        "overview": "Global IT services and consulting company within the Tata Group.",
        "business_model": "Services-led digital transformation, applications, and cloud engagements.",
        "segments": ["Banking & Financial Services", "Consumer", "Life Sciences", "Manufacturing"],
        "geographies": ["North America", "Europe", "India", "APAC"],
        "competitors": ["INFY", "WIPRO", "HCLTECH"],
        "industry_position": "Top-tier global IT services franchise.",
        "ir_url": "https://www.tcs.com/investor-relations",
        "annual_url": "https://www.tcs.com/investor-relations",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "seed_claims": [
            {
                "field": "company_overview",
                "claim": "TCS is a global IT services leader focused on digital transformation and enterprise technology services.",
                "source": "TCS Investor Relations",
                "url": "https://www.tcs.com/investor-relations",
                "section": "Overview",
                "authority": 10,
                "connector": "company_ir",
            },
            {
                "field": "risks",
                "claim": "Key risks include demand cyclicality in large accounts, wage inflation, and currency movement.",
                "source": "TCS IR / annual disclosures",
                "url": "https://www.tcs.com/investor-relations",
                "section": "Risks",
                "authority": 10,
                "connector": "company_ir",
            },
        ],
        "timeline_seed": [
            {"year": 2018, "title": "Large-deal digital transformation cycle", "category": "strategy"},
            {"year": 2023, "title": "GenAI service offerings expansion", "category": "product"},
            {"year": 2026, "title": "Latest quarterly monitoring window", "category": "monitoring"},
        ],
        "financial_seed": {
            "revenue_inr_cr_p50": 260000.0,
            "ebitda_margin_p50": 0.25,
            "eps_p50": 140.0,
            "net_debt_p50": -30000.0,
            "roe_p50": 0.45,
            "target_multiple_p50": 28.0,
        },
    },
    "INFY": {
        "company": "Infosys",
        "aliases": ["infosys", "infy"],
        "overview": "Global digital services and consulting company.",
        "business_model": "IT services, digital, cloud, and consulting engagements.",
        "segments": ["Financial Services", "Retail", "Communications", "Energy & Utilities"],
        "geographies": ["North America", "Europe", "India", "ROW"],
        "competitors": ["TCS", "WIPRO", "HCLTECH"],
        "industry_position": "Top-tier Indian IT services exporter.",
        "ir_url": "https://www.infosys.com/investors.html",
        "annual_url": "https://www.infosys.com/investors/reports-filings.html",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "seed_claims": [
            {
                "field": "company_overview",
                "claim": "Infosys provides digital services and consulting globally with large North America exposure.",
                "source": "Infosys Investors",
                "url": "https://www.infosys.com/investors.html",
                "section": "Overview",
                "authority": 10,
                "connector": "company_ir",
            }
        ],
        "timeline_seed": [
            {"year": 2022, "title": "Cloud and digital large-deal focus", "category": "strategy"},
            {"year": 2026, "title": "Latest IR / guidance monitoring", "category": "monitoring"},
        ],
        "financial_seed": {
            "revenue_inr_cr_p50": 165000.0,
            "ebitda_margin_p50": 0.23,
            "eps_p50": 70.0,
            "net_debt_p50": -25000.0,
            "roe_p50": 0.30,
            "target_multiple_p50": 25.0,
        },
    },
    "HDFCBANK": {
        "company": "HDFC Bank",
        "aliases": ["hdfc bank", "hdfcbank", "hdfc"],
        "overview": "Private sector bank with large retail and wholesale franchises in India.",
        "business_model": "Spread + fee income banking franchise with deposit-led funding.",
        "segments": ["Retail Banking", "Wholesale Banking", "Treasury"],
        "geographies": ["India"],
        "competitors": ["ICICIBANK", "SBIN", "KOTAKBANK"],
        "industry_position": "Leading private bank franchise by deposits/loans cohort.",
        "ir_url": "https://www.hdfcbank.com/personal/about-us/investor-relations",
        "annual_url": "https://www.hdfcbank.com/personal/about-us/investor-relations",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "seed_claims": [
            {
                "field": "company_overview",
                "claim": "HDFC Bank is a leading Indian private sector bank with a large retail franchise.",
                "source": "HDFC Bank Investor Relations",
                "url": "https://www.hdfcbank.com/personal/about-us/investor-relations",
                "section": "Overview",
                "authority": 10,
                "connector": "company_ir",
            }
        ],
        "timeline_seed": [
            {"year": 2023, "title": "HDFC Ltd merger integration era", "category": "m_and_a"},
            {"year": 2026, "title": "Post-merger deposit/loan mix monitoring", "category": "monitoring"},
        ],
        "financial_seed": {
            "revenue_inr_cr_p50": 180000.0,
            "ebitda_margin_p50": 0.0,
            "eps_p50": 95.0,
            "net_debt_p50": 0.0,
            "roe_p50": 0.15,
            "target_multiple_p50": 2.8,
        },
    },
}


def resolve_ticker(text: str | None) -> str | None:
    if not text:
        return None
    raw = text.strip().upper()
    if raw in COMPANIES:
        return raw
    low = text.lower()
    for ticker, profile in COMPANIES.items():
        for alias in profile.get("aliases") or []:
            if alias in low:
                return ticker
        if profile["company"].lower() in low:
            return ticker
    # bare symbol-ish token
    for token in text.replace("?", " ").replace(",", " ").split():
        t = token.strip().upper()
        if t in COMPANIES:
            return t
    return None
