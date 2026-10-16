"""FAA source authority scores — contribute to FRE ranking via document.authority."""

from __future__ import annotations

AUTHORITY_BY_TYPE: dict[str, int] = {
    "annual_report": 10,
    "quarterly_report": 10,
    "exchange_filing": 10,
    "nse_bse_filing": 10,
    "sec_filing": 10,
    "government": 9,
    "government_notification": 9,
    "regulatory_circular": 9,
    "rbi": 9,
    "sebi": 9,
    "conference_call": 9,
    "conference_call_transcript": 9,
    "transcript": 9,
    "investor_presentation": 8,
    "reuters": 8,
    "bloomberg": 8,
    "industry_report": 6,
    "news": 7,
    "rss": 7,
    "wikipedia": 3,
    "general_web": 3,
    "unknown_blog": 1,
    "unknown": 1,
}

AUTHORITY_BY_CONNECTOR: dict[str, int] = {
    "company_ir": 10,
    "nse": 10,
    "bse": 10,
    "sebi": 9,
    "rbi": 9,
    "mca": 9,
    "pib": 9,
    "government": 9,
    "news": 7,
    "rss": 7,
    "pdf_url": 8,
    "html_page": 3,
    "search_api": 3,
    "tavily": 3,
    "exa": 3,
    "serpapi": 3,
    "google_cse": 3,
    "bing": 3,
}


def faa_authority(
    document_type: str | None = None,
    connector_id: str | None = None,
    *,
    organisation: str | None = None,
    override: int | None = None,
) -> int:
    if override is not None:
        try:
            return max(1, min(10, int(override)))
        except Exception:
            pass
    org = (organisation or "").lower()
    if "reuters" in org:
        return 8
    if "bloomberg" in org:
        return 8
    if "wikipedia" in org:
        return 3
    for key in (document_type, connector_id):
        if not key:
            continue
        k = key.lower()
        if k in AUTHORITY_BY_TYPE:
            return AUTHORITY_BY_TYPE[k]
        if k in AUTHORITY_BY_CONNECTOR:
            return AUTHORITY_BY_CONNECTOR[k]
    return 1
