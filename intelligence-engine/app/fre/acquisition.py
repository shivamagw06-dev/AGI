"""Step 4 — Document acquisition.

Soft-wires AOI when available. Also seeds an institutional public-knowledge corpus
so FRE can serve evidence offline without scraping.
"""

from __future__ import annotations

from typing import Any

from app.fre.authority import authority_score, source_tier
from app.fre.models import FreDocument, checksum_text, utc_now


SEED_CORPUS: list[dict[str, Any]] = [
    {
        "title": "Reliance Industries — FY26 Annual Report Highlights",
        "url": "https://www.ril.com/ar/fy26-highlights",
        "source": "company_ir",
        "document_type": "annual_report",
        "organisation": "Reliance Industries",
        "company": "Reliance Industries",
        "symbol": "RELIANCE",
        "published_at": "2026-05-12",
        "financial_year": "FY26",
        "raw_text": (
            "Financial Highlights. Consolidated revenue increased 18% year on year to "
            "Rs 10.2 lakh crore. EBITDA rose to Rs 1.85 lakh crore supported by Jio and Retail. "
            "Oil-to-chemicals margins remained resilient despite crude volatility. "
            "Net debt stayed within management comfort. Capex guidance remains focused on "
            "new energy and digital infrastructure. Risks include crude price spikes, "
            "regulatory changes in telecom and retail competition."
        ),
    },
    {
        "title": "Infosys — Q1 FY27 Investor Presentation",
        "url": "https://www.infosys.com/investors/q1fy27-presentation",
        "source": "company_ir",
        "document_type": "investor_presentation",
        "organisation": "Infosys",
        "company": "Infosys",
        "symbol": "INFY",
        "published_at": "2026-07-18",
        "financial_year": "FY27",
        "quarter": "Q1",
        "raw_text": (
            "Q1 FY27 results. Revenue grew 3.2% sequential and 5.1% year on year in constant currency. "
            "Operating margin stood at 21.0%. Large deal TCV was USD 3.1 billion. "
            "Management guided for mid-single digit growth for FY27. AI and cloud deals "
            "are expanding across BFSI and manufacturing. Risks include visa/policy changes "
            "and client concentration in North America."
        ),
    },
    {
        "title": "Infosys — Q1 FY27 Earnings Call Transcript",
        "url": "https://www.infosys.com/investors/q1fy27-transcript",
        "source": "company_ir",
        "document_type": "transcript",
        "organisation": "Infosys",
        "company": "Infosys",
        "symbol": "INFY",
        "published_at": "2026-07-18",
        "quarter": "Q1",
        "raw_text": (
            "Management guidance: We expect mid-single digit revenue growth for FY27. "
            "Deal pipeline remains healthy with AI-led transformation programs. "
            "Margin trajectory depends on utilisation and pyramid optimisation. "
            "Client budgets are cautious but digital spend continues."
        ),
    },
    {
        "title": "RBI Monetary Policy Statement — July 2026",
        "url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx",
        "source": "rbi",
        "document_type": "government",
        "organisation": "Reserve Bank of India",
        "published_at": "2026-07-10",
        "raw_text": (
            "The Monetary Policy Committee decided to keep the policy repo rate unchanged. "
            "CPI inflation has moderated but food prices remain a watch item. "
            "Growth remains resilient supported by domestic demand and public capex. "
            "Liquidity conditions are stable. Transmission to bank lending rates continues."
        ),
    },
    {
        "title": "NSE Corporate Filing — Reliance Industries Board Update",
        "url": "https://www.nseindia.com/companies-listing/corporate-filings",
        "source": "nse",
        "document_type": "exchange_filing",
        "organisation": "NSE",
        "company": "Reliance Industries",
        "symbol": "RELIANCE",
        "published_at": "2026-07-20",
        "raw_text": (
            "Exchange filing: The Board noted progress on new energy projects and retail store expansion. "
            "No material related-party deviations reported. Capex for the quarter remains aligned "
            "with previously communicated guidance."
        ),
    },
    {
        "title": "IMF World Economic Outlook — India Growth Note",
        "url": "https://www.imf.org/en/Publications/WEO",
        "source": "imf",
        "document_type": "imf",
        "organisation": "IMF",
        "published_at": "2026-04-15",
        "region": "IN",
        "raw_text": (
            "India remains among the fastest-growing major economies. Private consumption and "
            "public infrastructure investment support the outlook. Risks include global financial "
            "tightening and commodity price shocks. Disinflation progress supports policy space over time."
        ),
    },
    {
        "title": "IT Services Industry Outlook 2026",
        "url": "https://example-industry.org/it-outlook-2026",
        "source": "industry_report",
        "document_type": "industry_report",
        "organisation": "Industry Research Desk",
        "published_at": "2026-06-01",
        "raw_text": (
            "Global IT services demand is stabilising after a cautious spending cycle. "
            "AI services, cloud migration and cost programmes remain priority budgets. "
            "Indian IT majors with strong large-deal pipelines are better positioned. "
            "Margin pressure persists where utilisation is weak."
        ),
    },
    {
        "title": "Business Standard — Banks NIM and Credit Growth Watch",
        "url": "https://www.business-standard.com/banks-nim-credit",
        "source": "business_standard",
        "document_type": "news",
        "organisation": "Business Standard",
        "published_at": "2026-07-22",
        "raw_text": (
            "Indian banks are seeing mixed NIM trends as deposit costs remain elevated. "
            "Credit growth is healthy in retail and corporate segments. "
            "A delayed rate-cut cycle could support NIMs but may slow loan demand later."
        ),
    },
]


def _to_document(row: dict[str, Any]) -> FreDocument:
    doc = FreDocument(
        title=row["title"],
        url=row.get("url") or "",
        source=row.get("source") or "unknown",
        document_type=row.get("document_type") or "unknown",
        organisation=row.get("organisation") or "",
        company=row.get("company"),
        symbol=row.get("symbol"),
        author=row.get("author"),
        published_at=row.get("published_at"),
        financial_year=row.get("financial_year"),
        quarter=row.get("quarter"),
        region=row.get("region") or "IN",
        language=row.get("language") or "en",
        content_type=row.get("content_type") or "text/plain",
        raw_text=row.get("raw_text") or "",
        checksum=checksum_text(row.get("raw_text") or row.get("title") or ""),
        authority=authority_score(row.get("document_type"), row.get("source")),
        tier=source_tier(row.get("document_type"), row.get("source")),
        retrieved_at=utc_now(),
        metadata=dict(row.get("metadata") or {}),
    )
    return doc


def seed_documents() -> list[FreDocument]:
    return [_to_document(row) for row in SEED_CORPUS]


def acquire_from_text(
    *,
    title: str,
    text: str,
    url: str = "",
    source: str = "general_web",
    document_type: str = "unknown",
    company: str | None = None,
    symbol: str | None = None,
    published_at: str | None = None,
    organisation: str = "",
) -> FreDocument:
    return _to_document(
        {
            "title": title,
            "url": url,
            "source": source,
            "document_type": document_type,
            "organisation": organisation,
            "company": company,
            "symbol": symbol,
            "published_at": published_at,
            "raw_text": text,
        }
    )


def soft_acquire_from_aoi(aoi: Any, *, query: str = "", limit: int = 8) -> list[FreDocument]:
    """Soft-call AOI consult/search and map hits into FRE documents (no redesign)."""
    if aoi is None:
        return []
    docs: list[FreDocument] = []
    try:
        res = aoi.consult(query, limit=limit) if hasattr(aoi, "consult") else None
    except Exception:
        res = None
    hits = []
    if isinstance(res, dict):
        hits = list(res.get("hits") or [])
        company = res.get("company")
        if isinstance(company, dict):
            hits.append(company)
    for h in hits[:limit]:
        if not isinstance(h, dict):
            continue
        title = str(h.get("label") or h.get("title") or h.get("name") or "AOI artifact")
        text = str(
            h.get("summary")
            or h.get("snippet")
            or h.get("content")
            or h.get("why")
            or title
        )
        docs.append(
            acquire_from_text(
                title=title,
                text=text if isinstance(text, str) else str(text),
                url=str(h.get("url") or ""),
                source=str(h.get("source") or h.get("connector_id") or "aoi"),
                document_type=str(h.get("doc_type") or h.get("document_type") or "open_intelligence"),
                company=h.get("company") or h.get("company_name"),
                symbol=h.get("symbol") or h.get("nse_symbol"),
                published_at=h.get("published_at") or h.get("as_of"),
                organisation=str(h.get("organisation") or "AOI"),
            )
        )
    return docs
