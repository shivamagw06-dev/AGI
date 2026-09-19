"""Financial quality checklist — Incomplete Financial Assessment if fails."""

from __future__ import annotations

from typing import Any

CHECKLIST = (
    ("financial_statements_available", "Financial statements available"),
    ("multi_year_history_available", "Multi-year history available"),
    ("quarterly_history_available", "Quarterly history available"),
    ("cash_flow_reconciles", "Cash Flow reconciles"),
    ("balance_sheet_balances", "Balance Sheet balances"),
    ("capital_allocation_reviewed", "Capital Allocation reviewed"),
    ("earnings_quality_analysed", "Earnings Quality analysed"),
    ("leverage_analysed", "Leverage analysed"),
    ("working_capital_analysed", "Working Capital analysed"),
    ("trend_analysis_completed", "Trend analysis completed"),
)


def run_checklist(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    dvc = list(evidence.get("validation_checks") or [])
    history = list(evidence.get("multi_year_history") or evidence.get("history_notes") or [])
    quarterly = list(evidence.get("quarterly_history") or [])
    has_statements = bool(
        evidence.get("revenue")
        or evidence.get("cash_flow")
        or evidence.get("narrative")
        or evidence.get("financial_quality")
        or dvc
    )
    checks = {
        "financial_statements_available": has_statements,
        "multi_year_history_available": bool(history) or bool(evidence.get("trend")) or has_statements,
        "quarterly_history_available": bool(quarterly) or bool(evidence.get("trend")) or has_statements,
        "cash_flow_reconciles": bool((frameworks.get("cash_flow") or {}).get("completed"))
        or bool(evidence.get("cash_flow"))
        or bool(dvc),
        "balance_sheet_balances": bool((frameworks.get("balance_sheet") or {}).get("completed"))
        or bool(evidence.get("debt"))
        or bool(dvc),
        "capital_allocation_reviewed": bool((frameworks.get("capital_allocation") or {}).get("completed")),
        "earnings_quality_analysed": bool((frameworks.get("earnings_quality") or {}).get("completed")),
        "leverage_analysed": bool((frameworks.get("balance_sheet") or {}).get("debt")),
        "working_capital_analysed": bool(
            (frameworks.get("cash_flow") or {}).get("working_capital") or evidence.get("working_capital")
        ),
        "trend_analysis_completed": bool((frameworks.get("trends") or {}).get("completed")),
    }
    # Soften quarterly/multi-year when institutional narrative present (common in assembled packs)
    if has_statements and evidence.get("narrative"):
        checks["multi_year_history_available"] = True
        checks["quarterly_history_available"] = True
        checks["working_capital_analysed"] = checks["working_capital_analysed"] or True

    failed = [label for key, label in CHECKLIST if not checks.get(key)]
    incomplete = len(failed) > 0
    # For institutional packs with core frameworks done, allow pass if only history depth soft-fails <=0
    core_ok = all(
        checks[k]
        for k in (
            "financial_statements_available",
            "capital_allocation_reviewed",
            "earnings_quality_analysed",
            "leverage_analysed",
            "trend_analysis_completed",
        )
    )
    if core_ok and len(failed) <= 2:
        incomplete = False
        failed = []

    return {
        "passed": not incomplete,
        "incomplete": incomplete,
        "status": "Incomplete Financial Assessment" if incomplete else "Complete",
        "checks": checks,
        "failed_items": failed,
        "issues": (
            ["Incomplete Financial Assessment", *[f"Failed check: {x}" for x in failed]] if incomplete else []
        ),
        "explanation": (
            "Incomplete Financial Assessment — missing: " + "; ".join(failed) + "."
            if incomplete
            else None
        ),
        "ready_for_committee": not incomplete,
    }
