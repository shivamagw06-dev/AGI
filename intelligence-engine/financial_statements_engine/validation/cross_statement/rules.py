"""Cross-statement consistency checks."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import extract_metrics, finding, metric_value


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    metrics = extract_metrics(draft)
    out: list[dict[str, Any]] = []

    # If depreciation and capex both present — informational consistency (no hard identity)
    dep = metric_value(metrics, "depreciation")
    capex = metric_value(metrics, "capex")
    if dep is not None and capex is not None:
        out.append(
            finding(
                rule_id="XST_DEP_CAPEX",
                rule_name="depreciation_and_capex_present",
                status="PASS",
                severity="INFO",
                affected_metrics=["depreciation", "capex"],
                evidence={"depreciation": dep, "capex": capex},
            )
        )
    else:
        out.append(
            finding(
                rule_id="XST_DEP_CAPEX",
                rule_name="depreciation_and_capex_present",
                status="SKIP",
                severity="INFO",
                affected_metrics=["depreciation", "capex"],
            )
        )

    # Share capital ↔ EPS presence coupling
    sc = metric_value(metrics, "share_capital")
    eps = metric_value(metrics, "eps_basic")
    if sc is not None and eps is None:
        out.append(
            finding(
                rule_id="XST_EPS",
                rule_name="eps_with_share_capital",
                status="WARN",
                severity="WARNING",
                affected_metrics=["share_capital", "eps_basic"],
                detail="Share capital present without basic EPS",
            )
        )
    else:
        out.append(
            finding(
                rule_id="XST_EPS",
                rule_name="eps_with_share_capital",
                status="PASS" if sc is None or eps is not None else "SKIP",
                severity="INFO",
                affected_metrics=["share_capital", "eps_basic"],
            )
        )

    # Finance cost on IS vs debt on BS — soft
    fc = metric_value(metrics, "finance_cost")
    debt = metric_value(metrics, "total_debt")
    if fc is not None and fc > 0 and debt is None:
        out.append(
            finding(
                rule_id="XST_INTEREST_DEBT",
                rule_name="finance_cost_without_debt",
                status="WARN",
                severity="WARNING",
                affected_metrics=["finance_cost", "total_debt"],
                detail="Finance cost present without total_debt",
            )
        )
    else:
        out.append(
            finding(
                rule_id="XST_INTEREST_DEBT",
                rule_name="finance_cost_without_debt",
                status="PASS",
                severity="INFO",
                affected_metrics=["finance_cost", "total_debt"],
            )
        )

    # Tax expense vs PBT sign check
    tax = metric_value(metrics, "tax_expense")
    pbt = metric_value(metrics, "profit_before_tax")
    if tax is not None and pbt is not None and pbt > 0 and tax < 0:
        out.append(
            finding(
                rule_id="XST_TAX_SIGN",
                rule_name="tax_sign_vs_pbt",
                status="WARN",
                severity="WARNING",
                affected_metrics=["tax_expense", "profit_before_tax"],
                evidence={"tax": tax, "pbt": pbt},
            )
        )
    else:
        out.append(
            finding(
                rule_id="XST_TAX_SIGN",
                rule_name="tax_sign_vs_pbt",
                status="SKIP" if None in (tax, pbt) else "PASS",
                severity="INFO",
                affected_metrics=["tax_expense", "profit_before_tax"],
            )
        )

    return out
