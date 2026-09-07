"""Company canonical object (FSE-03 §5)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.cfdm.schema import COMPANY_STATUSES, REPORTING_STANDARDS
from financial_statements_engine.util import now_iso


def company_id_for(*, exchange: str, ticker: str, isin: str | None = None) -> str:
    if isin:
        return str(isin).strip().upper()
    return f"{str(exchange).upper().strip()}:{str(ticker).upper().strip()}"


def build_company(
    *,
    exchange: str,
    ticker: str,
    isin: str | None = None,
    legal_name: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    currency: str = "INR",
    reporting_standard: str = "IND_AS",
    fiscal_year_end: str = "03-31",
    status: str = "active",
    company_id: str | None = None,
) -> dict[str, Any]:
    if status not in COMPANY_STATUSES:
        raise ValueError(f"invalid company status: {status}")
    if reporting_standard not in REPORTING_STANDARDS:
        reporting_standard = "UNKNOWN"
    cid = company_id or company_id_for(exchange=exchange, ticker=ticker, isin=isin)
    return {
        "company_id": cid,
        "exchange": str(exchange).upper().strip(),
        "ticker": str(ticker).upper().strip(),
        "isin": isin,
        "legal_name": legal_name,
        "sector": sector,
        "industry": industry,
        "currency": currency,
        "reporting_standard": reporting_standard,
        "fiscal_year_end": fiscal_year_end,
        "status": status,
        "object": "company",
        "as_of": now_iso(),
    }
