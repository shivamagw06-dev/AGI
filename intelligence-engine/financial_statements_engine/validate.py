"""Legacy FSE-01 statement validation — status + issues only. Never edits metric values.

Canonical Draft validation for the warehouse gate is FSE-05 VFQE:
`financial_statements_engine.validation` (deterministic accounting engine).
"""

from __future__ import annotations

from typing import Any

from financial_statements_engine.registry import BALANCE_CANONICAL, CASHFLOW_CANONICAL, INCOME_CANONICAL

_CORE_INCOME = ("revenue", "net_income")
_CORE_BALANCE = ("total_assets", "total_equity")
_CORE_CASH = ("operating_cash_flow",)
_TOL = 0.05  # 5% relative tolerance for soft accounting identities


def _num(metrics: dict[str, Any], key: str) -> float | None:
    row = metrics.get(key)
    if row is None:
        return None
    if isinstance(row, dict):
        v = row.get("value_inr")
        if v is None:
            v = row.get("reported_value")
        return float(v) if isinstance(v, (int, float)) else None
    if isinstance(row, (int, float)):
        return float(row)
    return None


def _close(a: float | None, b: float | None, tol: float = _TOL) -> bool:
    if a is None or b is None:
        return True  # missing ⇒ skip, not fail identity
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol


def validate_statement(statement: dict[str, Any]) -> dict[str, Any]:
    """Return validation report; does not mutate statement metrics."""
    issues: list[dict[str, Any]] = []
    st = statement.get("statement_type")
    metrics = statement.get("metrics") or {}
    if st == "results_pack":
        parts = []
        for key in ("income_statement", "balance_sheet", "cash_flow"):
            part = statement.get(key)
            if isinstance(part, dict):
                parts.append(validate_statement(part))
        failed = any(p.get("validation_status") == "failed" for p in parts)
        flagged = any(p.get("validation_status") == "flagged" for p in parts)
        status = "failed" if failed else ("flagged" if flagged else "passed")
        for p in parts:
            issues.extend(p.get("issues") or [])
        tier = "tier_c_withheld" if failed else ("tier_b_flagged" if flagged else "tier_a_publish")
        return {
            "validation_status": status,
            "publication_tier": tier,
            "issues": issues,
            "parts": parts,
            "layer": "validation",
        }

    required = {
        "income_statement": _CORE_INCOME,
        "balance_sheet": _CORE_BALANCE,
        "cash_flow": _CORE_CASH,
    }.get(st, ())

    for key in required:
        if key not in metrics:
            issues.append({"code": "STRUCT_REQUIRED_KEYS", "metric": key, "severity": "error"})

    # Traceability
    for key, row in metrics.items():
        if isinstance(row, dict) and not row.get("evidence_id"):
            issues.append({"code": "TRACE_EVIDENCE", "metric": key, "severity": "error"})

    if st == "income_statement":
        pbt = _num(metrics, "profit_before_tax")
        tax = _num(metrics, "tax_expense")
        net_income = _num(metrics, "net_income")
        if pbt is not None and tax is not None and net_income is not None:
            if not _close(net_income, pbt - tax):
                issues.append(
                    {"code": "ACCT_IS_IDENTITY", "severity": "warning", "detail": "net_income !~ profit_before_tax - tax"}
                )

    if st == "balance_sheet":
        assets = _num(metrics, "total_assets")
        liab = _num(metrics, "total_liabilities")
        equity = _num(metrics, "total_equity")
        if assets is not None and liab is not None and equity is not None:
            if not _close(assets, liab + equity):
                issues.append({"code": "ACCT_BS_BALANCE", "severity": "warning", "detail": "assets !~ liab + equity"})

    if st == "cash_flow":
        ocf = _num(metrics, "operating_cash_flow")
        icf = _num(metrics, "investing_cash_flow")
        fcf = _num(metrics, "financing_cash_flow")
        net = _num(metrics, "net_cash_change")
        if net is None:
            net = _num(metrics, "net_change_in_cash")  # legacy synonym key if present pre-normalize
        if None not in (ocf, icf, fcf, net):
            if not _close(ocf + icf + fcf, net):  # type: ignore[operator]
                issues.append({"code": "ACCT_CF_BRIDGE", "severity": "warning", "detail": "OCF+ICF+FCF !~ net change"})

    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    if errors:
        status, tier = "failed", "tier_c_withheld"
    elif warnings:
        status, tier = "flagged", "tier_b_flagged"
    else:
        status, tier = "passed", "tier_a_publish"

    # Completeness soft flag
    catalog = {
        "income_statement": INCOME_CANONICAL,
        "balance_sheet": BALANCE_CANONICAL,
        "cash_flow": CASHFLOW_CANONICAL,
    }.get(st)
    if catalog:
        present = sum(1 for k in catalog if k in metrics)
        if present < max(2, len(required)):
            issues.append({"code": "COMPLETENESS_CORE", "severity": "warning", "present": present})

    return {
        "validation_status": status,
        "publication_tier": tier,
        "issues": issues,
        "layer": "validation",
    }


def apply_validation_status(statement: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow-copied statement with status fields set (metrics untouched)."""
    out = dict(statement)
    out["validation_status"] = report.get("validation_status")
    out["publication_tier"] = report.get("publication_tier")
    out["validation_issues"] = report.get("issues") or []
    if report.get("validation_status") == "failed":
        out["publication_status"] = "withheld"
    elif report.get("validation_status") == "flagged":
        out["publication_status"] = "flagged"
    else:
        out["publication_status"] = "published"
    return out
