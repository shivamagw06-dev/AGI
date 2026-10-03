"""Canonical financial / valuation history helpers for YFP enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from yfp.schema import YFP_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def financial_coverage(history: Dict[str, Any]) -> Dict[str, Any]:
    """Coverage / freshness / confidence for financial history package."""
    counts = history.get("counts") or {}
    required = (
        "income_annual",
        "balance_annual",
        "cashflow_annual",
    )
    present = sum(1 for k in required if int(counts.get(k) or 0) > 0)
    optional = (
        "income_quarterly",
        "balance_quarterly",
        "cashflow_quarterly",
    )
    opt_present = sum(1 for k in optional if int(counts.get(k) or 0) > 0)
    coverage = round((present / len(required)) * 0.7 + (opt_present / len(optional)) * 0.3, 4)

    # Key line items across latest annual income
    income = ((history.get("income_statement") or {}).get("annual") or [])
    balance = ((history.get("balance_sheet") or {}).get("annual") or [])
    cash = ((history.get("cash_flow") or {}).get("annual") or [])
    keys_ok = 0
    keys_total = 0
    for key in ("revenue", "ebitda", "ebit", "net_income", "eps"):
        keys_total += 1
        if income and (income[0].get("line_items") or {}).get(key) is not None:
            keys_ok += 1
    for key in ("total_assets", "total_liabilities", "shareholders_equity", "cash", "total_debt"):
        keys_total += 1
        if balance and (balance[0].get("line_items") or {}).get(key) is not None:
            keys_ok += 1
    for key in ("operating_cash_flow", "free_cash_flow", "capital_expenditure"):
        keys_total += 1
        if cash and (cash[0].get("line_items") or {}).get(key) is not None:
            keys_ok += 1
    field_cov = round(keys_ok / max(1, keys_total), 4)
    overall = round(coverage * 0.5 + field_cov * 0.5, 4)

    missing: List[str] = []
    checklist = [
        ("revenue", income, "revenue"),
        ("ebitda", income, "ebitda"),
        ("ebit", income, "ebit"),
        ("net_income", income, "net_income"),
        ("eps", income, "eps"),
        ("total_assets", balance, "total_assets"),
        ("total_liabilities", balance, "total_liabilities"),
        ("shareholders_equity", balance, "shareholders_equity"),
        ("cash", balance, "cash"),
        ("total_debt", balance, "total_debt"),
        ("operating_cash_flow", cash, "operating_cash_flow"),
        ("free_cash_flow", cash, "free_cash_flow"),
        ("capital_expenditure", cash, "capital_expenditure"),
    ]
    for name, rows, field in checklist:
        if not rows or (rows[0].get("line_items") or {}).get(field) is None:
            missing.append(name)

    return {
        "coverage": overall,
        "statement_coverage": coverage,
        "field_coverage": field_cov,
        "confidence": 0.72 if overall >= 0.5 else 0.55,
        "freshness": 1.0 if present else 0.0,
        "missing_financial_fields": missing,
        "counts": counts,
        "yfp_version": YFP_VERSION,
    }


def valuation_coverage(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    metrics = snapshot.get("metrics") or {}
    required = (
        "market_cap",
        "enterprise_value",
        "trailing_pe",
        "forward_pe",
        "ev_ebitda",
        "price_to_book",
        "price_to_sales",
        "peg",
        "dividend_yield",
        "beta",
        "shares_outstanding",
    )
    present = [k for k in required if metrics.get(k) is not None]
    missing = [k for k in required if k not in present]
    cov = round(len(present) / len(required), 4)
    return {
        "coverage": cov,
        "confidence": 0.74 if cov >= 0.5 else 0.58,
        "freshness": 1.0 if present else 0.0,
        "missing_valuation_fields": missing,
        "present": present,
        "yfp_version": YFP_VERSION,
    }


def series_from_history(
    history: Dict[str, Any],
    *,
    statement: str,
    field: str,
    period_type: str = "annual",
) -> List[Dict[str, Any]]:
    """Extract a field timeline from canonical history."""
    block = (history.get(statement) or {}).get(period_type) or []
    out = []
    for row in block:
        if not isinstance(row, dict):
            continue
        val = (row.get("line_items") or {}).get(field)
        if val is None:
            continue
        out.append(
            {
                "period_end": row.get("period_end"),
                "value": val,
                "field": field,
                "statement": statement,
                "period_type": period_type,
                "provider_id": "yahoo",
            }
        )
    return out


def kpi_trends(history: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Historical KPI trends for CID / Ask AGI (canonical fields only)."""
    trends: Dict[str, List[Dict[str, Any]]] = {}
    mapping = (
        ("income_statement", "revenue"),
        ("income_statement", "ebitda"),
        ("income_statement", "ebit"),
        ("income_statement", "net_income"),
        ("income_statement", "eps"),
        ("income_statement", "operating_income"),
        ("income_statement", "gross_profit"),
        ("balance_sheet", "total_assets"),
        ("balance_sheet", "total_liabilities"),
        ("balance_sheet", "shareholders_equity"),
        ("balance_sheet", "cash"),
        ("balance_sheet", "total_debt"),
        ("cash_flow", "operating_cash_flow"),
        ("cash_flow", "free_cash_flow"),
        ("cash_flow", "capital_expenditure"),
    )
    for stmt, field in mapping:
        series = series_from_history(history, statement=stmt, field=field, period_type="annual")
        if series:
            trends[field] = series
    return trends


def dvc_fields_from_valuation(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build DVC-compatible validated_field dicts for valuation metrics (Yahoo secondary)."""
    from dvc.models import make_validated_field

    metrics = snapshot.get("metrics") or {}
    symbol = str(snapshot.get("symbol") or "")
    out: Dict[str, Any] = {}
    for field, value in metrics.items():
        out[field] = make_validated_field(
            field=field,
            value=value,
            provider="yahoo",
            confidence=0.72,
            symbol=symbol,
            reason="yfp_valuation_history",
            validation_status="validated",
            observations=[{"provider": "yahoo", "value": value, "timestamp": _now()}],
        )
        # Annotate priority / consensus for mission metadata
        out[field]["provider_priority"] = 40
        out[field]["source"] = "Yahoo Finance"
        out[field]["consensus_status"] = "single_source_secondary"
    return out


def summarize_changes(history: Dict[str, Any]) -> Dict[str, Any]:
    """Financial changes summary for LEO evidence package."""
    income = ((history.get("income_statement") or {}).get("annual") or [])
    cash = ((history.get("cash_flow") or {}).get("annual") or [])
    balance = ((history.get("balance_sheet") or {}).get("annual") or [])

    def _chg(rows: list, field: str) -> Optional[float]:
        if len(rows) < 2:
            return None
        a = (rows[0].get("line_items") or {}).get(field)
        b = (rows[1].get("line_items") or {}).get(field)
        if a is None or b in (None, 0):
            return None
        try:
            return round((float(a) - float(b)) / abs(float(b)) * 100.0, 4)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    return {
        "revenue_growth_pct": _chg(income, "revenue"),
        "ebitda_growth_pct": _chg(income, "ebitda"),
        "net_income_growth_pct": _chg(income, "net_income"),
        "operating_margin_proxy": None,
        "ocf_growth_pct": _chg(cash, "operating_cash_flow"),
        "fcf_growth_pct": _chg(cash, "free_cash_flow"),
        "debt_change_pct": _chg(balance, "total_debt"),
        "equity_change_pct": _chg(balance, "shareholders_equity"),
        "as_of": _now(),
        "yfp_version": YFP_VERSION,
    }
