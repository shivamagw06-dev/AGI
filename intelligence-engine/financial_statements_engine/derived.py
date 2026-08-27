"""FSE-01 legacy derived helpers — thin façade.

Authoritative calculations live in FSE-07 Derived Metrics Engine:
`financial_statements_engine.derived_metrics`.
"""

from __future__ import annotations

from typing import Any

from financial_statements_engine.util import now_iso, write_json_atomic
from financial_statements_engine.store import paths_for


def _v(metrics: dict[str, Any], key: str) -> float | None:
    row = metrics.get(key)
    if isinstance(row, dict):
        val = row.get("value_inr")
        return float(val) if isinstance(val, (int, float)) else None
    return float(row) if isinstance(row, (int, float)) else None


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_derived(statement: dict[str, Any]) -> dict[str, Any]:
    """Legacy FSE-01 statement-pack helper. Prefer derived_metrics.production.calculate."""
    metrics = statement.get("metrics") or {}
    if statement.get("statement_type") == "results_pack":
        metrics = {}
        for part_key in ("income_statement", "balance_sheet", "cash_flow"):
            part = statement.get(part_key) or {}
            metrics.update(part.get("metrics") or {})

    revenue = _v(metrics, "revenue")
    net_income = _v(metrics, "net_income")
    if net_income is None:
        net_income = _v(metrics, "pat")
    ebit = _v(metrics, "ebit")
    ebitda = _v(metrics, "ebitda")
    equity = _v(metrics, "total_equity")
    assets = _v(metrics, "total_assets")
    ocf = _v(metrics, "operating_cash_flow")

    derived = {
        "net_income_margin": _safe_div(net_income, revenue),
        "pat_margin": _safe_div(net_income, revenue),
        "ebit_margin": _safe_div(ebit, revenue),
        "ebitda_margin": _safe_div(ebitda, revenue),
        "roe": _safe_div(net_income, equity),
        "roa": _safe_div(net_income, assets),
        "ocf_to_net_income": _safe_div(ocf, net_income),
        "ocf_to_pat": _safe_div(ocf, net_income),
    }
    return {
        "ticker": statement.get("ticker"),
        "period_end": statement.get("period_end"),
        "derived": True,
        "metrics": derived,
        "source_statement_id": statement.get("statement_id"),
        "as_of": now_iso(),
        "layer": "derived_metrics",
        "overwrites_reported": False,
        "authoritative": False,
        "prefer": "financial_statements_engine.derived_metrics.production.calculate",
    }


def persist_derived(ticker: str, derived_doc: dict[str, Any]) -> dict[str, Any]:
    path = paths_for(ticker.upper().strip())["derived"] / "latest.json"
    write_json_atomic(path, derived_doc)
    return derived_doc
