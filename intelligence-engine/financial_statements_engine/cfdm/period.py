"""Reporting Period canonical object (FSE-03 §6)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.cfdm.schema import CONSOLIDATION_TYPES, PERIOD_KINDS, STATEMENT_SCOPES
from financial_statements_engine.util import now_iso


def period_id_for(
    *,
    company_id: str,
    period_end: str,
    period_kind: str,
    consolidation_type: str,
) -> str:
    return f"{company_id}:{period_end}:{period_kind}:{consolidation_type}"


def build_period(
    *,
    company_id: str,
    period_end: str,
    period_kind: str = "annual",
    consolidation_type: str = "consolidated",
    statement_scope: str = "as_reported",
    statement_date: str | None = None,
    filing_date: str | None = None,
    period_start: str | None = None,
    fiscal_year: int | None = None,
    quarter: str | None = None,
    period_id: str | None = None,
) -> dict[str, Any]:
    if period_kind not in PERIOD_KINDS:
        raise ValueError(f"invalid period_kind: {period_kind}")
    if consolidation_type not in CONSOLIDATION_TYPES:
        raise ValueError(f"invalid consolidation_type: {consolidation_type}")
    if statement_scope not in STATEMENT_SCOPES:
        raise ValueError(f"invalid statement_scope: {statement_scope}")
    pid = period_id or period_id_for(
        company_id=company_id,
        period_end=period_end,
        period_kind=period_kind,
        consolidation_type=consolidation_type,
    )
    return {
        "period_id": pid,
        "company_id": company_id,
        "statement_date": statement_date,
        "filing_date": filing_date,
        "period_start": period_start,
        "period_end": period_end,
        "fiscal_year": fiscal_year,
        "quarter": quarter,
        "period_kind": period_kind,
        "statement_scope": statement_scope,
        "consolidation_type": consolidation_type,
        "object": "reporting_period",
        "as_of": now_iso(),
    }
