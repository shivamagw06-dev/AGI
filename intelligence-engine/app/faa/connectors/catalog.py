"""Known public IR / exchange / gov URL patterns for intelligent discovery."""

from __future__ import annotations

from typing import Any

# High-signal public landing pages / report hubs (not scraped blindly — discovered as candidates).
COMPANY_IR: dict[str, dict[str, Any]] = {
    "RELIANCE": {
        "company": "Reliance Industries",
        "ir_home": "https://www.ril.com/InvestorRelations/Overview.aspx",
        "annual": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
        "quarterly": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
        "presentation": "https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
        "news": "https://www.ril.com/Media/MediaRoom.aspx",
    },
    "INFY": {
        "company": "Infosys",
        "ir_home": "https://www.infosys.com/investors.html",
        "annual": "https://www.infosys.com/investors/reports-filings.html",
        "quarterly": "https://www.infosys.com/investors/reports-filings/quarterly-results.html",
        "presentation": "https://www.infosys.com/investors/reports-filings.html",
        "transcript": "https://www.infosys.com/investors/reports-filings.html",
        "news": "https://www.infosys.com/newsroom.html",
    },
    "TCS": {
        "company": "Tata Consultancy Services",
        "ir_home": "https://www.tcs.com/investor-relations",
        "annual": "https://www.tcs.com/investor-relations",
        "quarterly": "https://www.tcs.com/investor-relations",
        "presentation": "https://www.tcs.com/investor-relations",
        "news": "https://www.tcs.com/newsroom",
    },
    "HDFCBANK": {
        "company": "HDFC Bank",
        "ir_home": "https://www.hdfcbank.com/personal/about-us/investor-relations",
        "annual": "https://www.hdfcbank.com/personal/about-us/investor-relations",
        "quarterly": "https://www.hdfcbank.com/personal/about-us/investor-relations",
        "news": "https://www.hdfcbank.com/personal/about-us/news-room",
    },
}

EXCHANGE_URLS = {
    "nse_filings": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
    "nse_equity": "https://www.nseindia.com/get-quotes/equity",
    "bse_announcements": "https://www.bseindia.com/corporates/ann.html",
    "sebi": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10",
    "rbi_press": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
    "rbi_mp": "https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx",
}


def resolve_symbol(company: str | None, symbol: str | None) -> str | None:
    if symbol:
        return symbol.upper()
    if not company:
        return None
    c = company.lower()
    aliases = {
        "reliance": "RELIANCE",
        "reliance industries": "RELIANCE",
        "ril": "RELIANCE",
        "infosys": "INFY",
        "infy": "INFY",
        "tcs": "TCS",
        "tata consultancy": "TCS",
        "hdfc bank": "HDFCBANK",
        "hdfcbank": "HDFCBANK",
    }
    for k, v in aliases.items():
        if k in c:
            return v
    return None
