"""Materiality engine — ignore cosmetic wording; focus on thesis-capable changes."""

from __future__ import annotations

from typing import Any

# Absolute / relative thresholds by metric family
CRITICAL_METRICS = {"Guidance_Status", "Impairment", "CEO_Change", "Auditor_Change", "Dividend_cut"}
HIGH_METRICS = {"NIM", "CASA", "CET1", "ROE", "ROIC", "GNPA", "Revenue_Growth", "Operating_Margin"}


def classify_materiality(
    *,
    metric: str,
    domain: str,
    previous: Any,
    current: Any,
    change_type: str,
    cosmetic: bool = False,
) -> str:
    if cosmetic:
        return "ignore"
    if metric in CRITICAL_METRICS or change_type in {"withdrawn", "dividend_cut", "impairment_added", "ceo_change"}:
        return "critical"
    if isinstance(previous, (int, float)) and isinstance(current, (int, float)):
        base = abs(float(previous)) + 1e-9
        rel = abs(float(current) - float(previous)) / base
        abs_delta = abs(float(current) - float(previous))
        if metric in HIGH_METRICS:
            if rel >= 0.05 or abs_delta >= 0.15:
                return "high"
            if rel >= 0.02 or abs_delta >= 0.05:
                return "medium"
            return "low"
        if rel >= 0.10:
            return "high"
        if rel >= 0.03:
            return "medium"
        return "low"
    if domain in {"guidance", "risks", "capital", "accounting"} and previous != current:
        return "high"
    if domain == "management" and change_type in {"new_warning", "optimism_decreased", "changed_outlook"}:
        return "high"
    if previous != current:
        return "medium"
    return "ignore"


def thesis_impact(materiality: str, change_type: str, metric: str, previous: Any, current: Any) -> str:
    if materiality == "ignore":
        return "neutral"
    if change_type in {"policy_added", "policy_removed"}:
        return "needs_committee_review"
    weaker_types = {
        "margin_compression",
        "revenue_deceleration",
        "working_capital_deterioration",
        "lowered",
        "withdrawn",
        "optimism_decreased",
        "new_warning",
        "risk_added",
        "dividend_cut",
        "debt_increase",
        "casa_decline",
        "capital_ratio_decline",
        "roe_decline",
    }
    stronger_types = {
        "margin_expansion",
        "revenue_acceleration",
        "raised",
        "optimism_increased",
        "risk_removed",
        "dividend_increase",
        "buyback",
        "debt_repayment",
        "capital_ratio_increase",
    }
    if change_type in weaker_types:
        return "weakens_thesis" if materiality in {"critical", "high"} else "needs_committee_review"
    if change_type in stronger_types:
        return "strengthens_thesis" if materiality in {"critical", "high"} else "neutral"
    # numeric direction heuristics
    if isinstance(previous, (int, float)) and isinstance(current, (int, float)):
        lower_better = metric in {"GNPA", "NNPA", "Credit_Cost", "Attrition"}
        improved = (current < previous) if lower_better else (current > previous)
        if materiality in {"critical", "high"}:
            return "strengthens_thesis" if improved else "weakens_thesis"
        return "needs_committee_review"
    return "unknown"
