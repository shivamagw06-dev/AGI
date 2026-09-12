"""Configurable accounting equation rules."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import close, extract_metrics, finding, metric_value
from financial_statements_engine.validation.schema import ACCOUNTING_TOLERANCE

# (rule_id, name, left_keys_sum, right_keys_sum) — missing sides ⇒ SKIP
AccountingEq = tuple[str, str, tuple[str, ...], tuple[str, ...]]

DEFAULT_EQUATIONS: tuple[AccountingEq, ...] = (
    ("ACCT_BS_IDENTITY", "assets_eq_liabilities_plus_equity", ("total_assets",), ("total_liabilities", "total_equity")),
    (
        "ACCT_CA_NCA",
        "current_plus_noncurrent_assets_eq_total",
        ("current_assets", "non_current_assets"),
        ("total_assets",),
    ),
    (
        "ACCT_CL_NCL",
        "current_plus_noncurrent_liabilities_eq_total",
        ("current_liabilities", "non_current_liabilities"),
        ("total_liabilities",),
    ),
    (
        "ACCT_CF_BRIDGE",
        "ocf_icf_fcf_eq_net_cash_change",
        ("operating_cash_flow", "investing_cash_flow", "financing_cash_flow"),
        ("net_cash_change",),
    ),
    ("ACCT_IS_PAT", "pbt_minus_tax_eq_net_income", ("profit_before_tax",), ("tax_expense", "net_income")),
)


def _sum_keys(metrics: dict[str, Any], keys: tuple[str, ...]) -> tuple[float | None, list[str]]:
    vals = []
    present = []
    for k in keys:
        v = metric_value(metrics, k)
        if v is None:
            return None, present
        vals.append(v)
        present.append(k)
    return sum(vals), present


def run(
    draft: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
    equations: tuple[AccountingEq, ...] | None = None,
    tolerance: float | None = None,
) -> list[dict[str, Any]]:
    tol = float(tolerance if tolerance is not None else ACCOUNTING_TOLERANCE)
    metrics = extract_metrics(draft)
    out: list[dict[str, Any]] = []
    eqs = equations or DEFAULT_EQUATIONS

    for rule_id, name, left_keys, right_keys in eqs:
        # Special-case PBT - tax ~= NI (right is not a plain sum)
        if rule_id == "ACCT_IS_PAT":
            pbt = metric_value(metrics, "profit_before_tax")
            tax = metric_value(metrics, "tax_expense")
            ni = metric_value(metrics, "net_income")
            if None in (pbt, tax, ni):
                out.append(
                    finding(
                        rule_id=rule_id,
                        rule_name=name,
                        status="SKIP",
                        severity="INFO",
                        affected_metrics=["profit_before_tax", "tax_expense", "net_income"],
                        evidence={"reason": "insufficient_metrics"},
                    )
                )
                continue
            ok = close(ni, (pbt or 0) - (tax or 0), tol)
            out.append(
                finding(
                    rule_id=rule_id,
                    rule_name=name,
                    status="PASS" if ok else "FAIL",
                    severity="ERROR" if not ok else "INFO",
                    affected_metrics=["profit_before_tax", "tax_expense", "net_income"],
                    evidence={"pbt": pbt, "tax": tax, "net_income": ni, "tolerance": tol},
                    detail=None if ok else "net_income !~ profit_before_tax - tax_expense",
                )
            )
            continue

        left, left_present = _sum_keys(metrics, left_keys)
        right, right_present = _sum_keys(metrics, right_keys)
        if left is None or right is None:
            out.append(
                finding(
                    rule_id=rule_id,
                    rule_name=name,
                    status="SKIP",
                    severity="INFO",
                    affected_metrics=list(left_keys) + list(right_keys),
                    evidence={"left_present": left_present, "right_present": right_present},
                )
            )
            continue
        ok = close(left, right, tol)
        out.append(
            finding(
                rule_id=rule_id,
                rule_name=name,
                status="PASS" if ok else "FAIL",
                severity="ERROR" if not ok else "INFO",
                affected_metrics=list(left_keys) + list(right_keys),
                evidence={"left": left, "right": right, "tolerance": tol},
                detail=None if ok else f"{name} identity failed",
            )
        )
    return out
