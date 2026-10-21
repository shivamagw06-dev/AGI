"""Canonical Statement Layer — standardized IS / BS / CF documents."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.registry import BALANCE_CANONICAL, CASHFLOW_CANONICAL, INCOME_CANONICAL
from financial_statements_engine.schema import STATEMENT_TYPES
from financial_statements_engine.util import now_iso


def _pick(metrics: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: metrics[k] for k in keys if k in metrics}


def build_statement(
    *,
    ticker: str,
    statement_type: str,
    period_type: str,
    period_end: str,
    metrics: dict[str, Any],
    evidence_id: str | None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    currency: str = "INR",
    version: int = 1,
    entity: str | None = None,
    extractor: str | None = None,
) -> dict[str, Any]:
    if statement_type not in STATEMENT_TYPES:
        raise ValueError(f"unsupported statement_type: {statement_type}")

    if statement_type == "income_statement":
        selected = _pick(metrics, INCOME_CANONICAL)
    elif statement_type == "balance_sheet":
        selected = _pick(metrics, BALANCE_CANONICAL)
    elif statement_type == "cash_flow":
        selected = _pick(metrics, CASHFLOW_CANONICAL)
    else:
        selected = dict(metrics)

    # Attach evidence to each metric if missing
    enriched: dict[str, Any] = {}
    for k, v in selected.items():
        row = dict(v) if isinstance(v, dict) else {"value_inr": v}
        if evidence_id and not row.get("evidence_id"):
            row["evidence_id"] = evidence_id
        if extractor and not row.get("extractor"):
            row["extractor"] = extractor
        enriched[k] = row

    t = ticker.upper().strip()
    stmt_id = f"{t}:{period_type}:{period_end}:{statement_type}:v{version}"
    return {
        "statement_id": stmt_id,
        "ticker": t,
        "entity": entity or t,
        "statement_type": statement_type,
        "period_type": period_type,
        "period_end": period_end,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "currency": currency,
        "metrics": enriched,
        "version": version,
        "publication_status": "draft",
        "validation_status": "pending",
        "as_of": now_iso(),
        "layer": "canonical",
    }


def build_results_pack(
    *,
    ticker: str,
    period_type: str,
    period_end: str,
    metrics: dict[str, Any],
    evidence_id: str | None,
    **kwargs: Any,
) -> dict[str, Any]:
    income = build_statement(
        ticker=ticker,
        statement_type="income_statement",
        period_type=period_type,
        period_end=period_end,
        metrics=metrics,
        evidence_id=evidence_id,
        **kwargs,
    )
    balance = build_statement(
        ticker=ticker,
        statement_type="balance_sheet",
        period_type=period_type,
        period_end=period_end,
        metrics=metrics,
        evidence_id=evidence_id,
        **kwargs,
    )
    cash = build_statement(
        ticker=ticker,
        statement_type="cash_flow",
        period_type=period_type,
        period_end=period_end,
        metrics=metrics,
        evidence_id=evidence_id,
        **kwargs,
    )
    t = ticker.upper().strip()
    version = int(kwargs.get("version") or 1)
    return {
        "statement_id": f"{t}:{period_type}:{period_end}:results_pack:v{version}",
        "ticker": t,
        "entity": kwargs.get("entity") or t,
        "statement_type": "results_pack",
        "period_type": period_type,
        "period_end": period_end,
        "fiscal_year": kwargs.get("fiscal_year"),
        "fiscal_period": kwargs.get("fiscal_period"),
        "currency": kwargs.get("currency") or "INR",
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cash,
        "version": version,
        "publication_status": "draft",
        "validation_status": "pending",
        "as_of": now_iso(),
        "layer": "canonical",
    }
