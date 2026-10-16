"""Accounting red-flag library for institutional monitoring."""

from __future__ import annotations

from typing import Any


RED_FLAGS: list[dict[str, Any]] = [
    {
        "id": "revenue_faster_than_cash",
        "name": "Revenue rising faster than cash flow",
        "why": "Top-line growth without cash support often means accrual inflation or collection stress.",
        "severity": "high",
        "typical_causes": ["Aggressive revenue recognition", "Channel stuffing", "Deteriorating collections"],
        "false_positives": ["Lumpy contract cash timing", "Large customer prepayment shifts"],
        "monitoring_signals": ["Revenue growth vs CFO growth", "CFO/Sales trend", "DSO"],
        "related_concepts": ["revenue_recognition", "operating_cash_flow", "accounts_receivable"],
    },
    {
        "id": "receivables_faster_than_sales",
        "name": "Receivables growing faster than sales",
        "why": "Suggests revenue quality issues or weakening customer credit.",
        "severity": "high",
        "typical_causes": ["Pulled-forward revenue", "Extended credit to hit targets", "Channel loading"],
        "false_positives": ["Mix shift to longer-cycle customers", "FX translation"],
        "monitoring_signals": ["DSO", "AR/Sales", "Allowance ratio"],
        "related_concepts": ["accounts_receivable", "revenue_recognition", "accruals"],
    },
    {
        "id": "inventory_accumulation",
        "name": "Inventory accumulation",
        "why": "Ties cash and foreshadows markdowns/write-downs that hit future earnings.",
        "severity": "medium",
        "typical_causes": ["Demand miss", "Production overshoot", "Obsolete stock"],
        "false_positives": ["Strategic pre-buy ahead of price rises", "New product ramp"],
        "monitoring_signals": ["Inventory days", "Inventory/Sales", "Gross margin"],
        "related_concepts": ["inventory", "working_capital", "cogs"],
    },
    {
        "id": "capitalising_opex",
        "name": "Capitalising operating expenses",
        "why": "Moves cash opex into assets, inflating current earnings and ROIC optics.",
        "severity": "high",
        "typical_causes": ["Aggressive capitalisation policy", "KPI-linked incentives"],
        "false_positives": ["Legitimate software capitalisation under standards"],
        "monitoring_signals": ["Capex vs peers", "Capitalised development / opex", "Amortisation lag"],
        "related_concepts": ["capitalised_expenses", "earnings_quality", "free_cash_flow"],
    },
    {
        "id": "frequent_exceptionals",
        "name": "Frequent exceptional items",
        "why": "Serial one-offs mean the 'adjusted' earnings are the real volatile business.",
        "severity": "medium",
        "typical_causes": ["Perpetual restructuring", "Earnings normalisation theatre"],
        "false_positives": ["Genuine multi-year transformation with cash costs"],
        "monitoring_signals": ["Exceptionals as % of EBIT each year", "Cash vs non-cash exceptionals"],
        "related_concepts": ["exceptional_items", "earnings_quality"],
    },
    {
        "id": "declining_cash_conversion",
        "name": "Declining cash conversion",
        "why": "Profits increasingly accrual-based; sustainability of earnings is falling.",
        "severity": "high",
        "typical_causes": ["WC blowout", "Accrual growth", "Margin quality fade"],
        "false_positives": ["Temporary growth investment year"],
        "monitoring_signals": ["CFO/NI", "CFO/EBITDA", "ΔNWC"],
        "related_concepts": ["earnings_quality", "operating_cash_flow", "accruals"],
    },
    {
        "id": "goodwill_without_returns",
        "name": "Rising goodwill without returns",
        "why": "Acquisition spend is not earning the cost of capital; impairment risk builds.",
        "severity": "medium",
        "typical_causes": ["Empire-building M&A", "Overpayment"],
        "false_positives": ["Early synergy years before returns show"],
        "monitoring_signals": ["Goodwill / equity", "ROIC including goodwill", "Impairment history"],
        "related_concepts": ["goodwill", "roic", "impairment"],
    },
    {
        "id": "large_impairments",
        "name": "Large impairment charges",
        "why": "Confirms past overstatement of asset values or failed strategy — often late.",
        "severity": "high",
        "typical_causes": ["Failed acquisitions", "Demand destruction", "Rate-driven value tests"],
        "false_positives": ["Conservative clean-up by new management (can be healthy)"],
        "monitoring_signals": ["Impairment size vs equity", "Subsequent ROIC", "Segment growth"],
        "related_concepts": ["impairment", "goodwill", "earnings_quality"],
    },
    {
        "id": "restated_statements",
        "name": "Restated financial statements",
        "why": "Prior numbers were unreliable; model history and trust must be rebuilt.",
        "severity": "critical",
        "typical_causes": ["Error", "Misapplication of standards", "Fraud"],
        "false_positives": ["Immaterial classification revisions"],
        "monitoring_signals": ["Restatement filings", "Audit opinions", "Internal control notes"],
        "related_concepts": ["restatements", "accounting_estimates", "earnings_quality"],
    },
]


def list_red_flags() -> dict[str, Any]:
    return {"count": len(RED_FLAGS), "red_flags": RED_FLAGS}


def score_red_flags(signals: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft heuristic: payload booleans/ratios trip matching flags."""
    p = {k.lower(): v for k, v in (signals or {}).items()}
    tripped = []
    mapping = {
        "revenue_faster_than_cash": p.get("revenue_growth", 0) > p.get("cfo_growth", 0) + 0.05
        if "revenue_growth" in p and "cfo_growth" in p
        else p.get("revenue_faster_than_cash"),
        "receivables_faster_than_sales": p.get("receivables_growth", 0) > p.get("sales_growth", 0) + 0.05
        if "receivables_growth" in p and "sales_growth" in p
        else p.get("receivables_faster_than_sales"),
        "inventory_accumulation": p.get("inventory_accumulation") or p.get("inventory_days_up"),
        "capitalising_opex": p.get("capitalising_opex"),
        "frequent_exceptionals": p.get("frequent_exceptionals") or (p.get("exceptionals_years", 0) >= 3),
        "declining_cash_conversion": p.get("cash_conversion", 1) < 0.8
        if "cash_conversion" in p
        else p.get("declining_cash_conversion"),
        "goodwill_without_returns": p.get("goodwill_without_returns"),
        "large_impairments": p.get("large_impairments"),
        "restated_statements": p.get("restated_statements") or p.get("restatement"),
    }
    by_id = {f["id"]: f for f in RED_FLAGS}
    for fid, active in mapping.items():
        if active:
            tripped.append(by_id[fid])
    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    max_sev = max((severity_rank.get(f["severity"], 0) for f in tripped), default=0)
    return {
        "tripped_count": len(tripped),
        "max_severity": {0: "none", 1: "medium", 2: "high", 3: "critical"}[max_sev],
        "tripped": tripped,
        "clean": not tripped,
    }
