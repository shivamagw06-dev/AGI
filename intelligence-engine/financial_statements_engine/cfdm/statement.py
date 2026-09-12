"""Statement canonical object (FSE-03 §7)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.cfdm.schema import STATEMENT_TYPES
from financial_statements_engine.util import now_iso


def statement_id_for(*, period_id: str, statement_type: str, version: int) -> str:
    return f"{period_id}:{statement_type}:v{int(version)}"


def build_statement(
    *,
    period_id: str,
    company_id: str,
    statement_type: str,
    version: int = 1,
    status: str = "draft",
    fact_ids: list[str] | None = None,
    currency: str = "INR",
) -> dict[str, Any]:
    if statement_type not in STATEMENT_TYPES:
        raise ValueError(f"invalid statement_type: {statement_type}")
    sid = statement_id_for(period_id=period_id, statement_type=statement_type, version=version)
    return {
        "statement_id": sid,
        "period_id": period_id,
        "company_id": company_id,
        "statement_type": statement_type,
        "version": int(version),
        "status": status,
        "currency": currency,
        "fact_ids": list(fact_ids or []),
        "immutable": status == "published",
        "object": "statement",
        "as_of": now_iso(),
    }
