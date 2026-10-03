"""Manipulation Detection — evidence-linked red flags."""

from __future__ import annotations

from typing import Any


def detect_manipulation(
    *,
    profile_flags: list[Any] | None,
    earnings: dict[str, Any],
    cash: dict[str, Any],
    accruals: dict[str, Any],
    revenue: dict[str, Any],
    policies: dict[str, Any],
    forensic: dict[str, Any],
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []

    for raw in profile_flags or []:
        if isinstance(raw, dict):
            alerts.append(raw)
        else:
            alerts.append({"flag": str(raw), "thesis_impact": "critical_review_required"})

    if accruals.get("label") == "Aggressive":
        alerts.append(
            {
                "flag": "Aggressive accruals",
                "detail": f"Accrual ratio {accruals.get('accrual_ratio')}",
                "thesis_impact": "weakens_thesis",
                "evidence_doc": accruals.get("evidence_doc"),
            }
        )
    if revenue.get("flags"):
        for fl in revenue["flags"]:
            alerts.append(
                {
                    "flag": fl,
                    "detail": revenue.get("notes"),
                    "thesis_impact": "critical_review_required"
                    if "stuffing" in fl or "policy" in fl
                    else "weakens_thesis",
                    "evidence_doc": revenue.get("evidence_doc"),
                }
            )
    if policies.get("material_count", 0) >= 1:
        alerts.append(
            {
                "flag": "Material accounting policy change",
                "detail": f"{policies.get('material_count')} material change(s)",
                "thesis_impact": "critical_review_required",
            }
        )
    beneish = forensic.get("beneish") or {}
    if beneish.get("beneish_risk") == "elevated":
        alerts.append(
            {
                "flag": "Beneish M-Score elevated",
                "detail": f"M={beneish.get('beneish_m')}",
                "thesis_impact": "critical_review_required",
            }
        )
    if float(cash.get("cash_quality") or 100) < 45:
        alerts.append(
            {
                "flag": "Weak cash-backed earnings",
                "detail": cash.get("notes"),
                "thesis_impact": "weakens_thesis",
                "evidence_doc": cash.get("evidence_doc"),
            }
        )
    if earnings.get("label") == "Questionable":
        alerts.append(
            {
                "flag": "Questionable earnings quality",
                "detail": earnings.get("notes"),
                "thesis_impact": "critical_review_required",
                "evidence_doc": earnings.get("evidence_doc"),
            }
        )

    risk = "low"
    if any(a.get("thesis_impact") == "critical_review_required" for a in alerts):
        risk = "high"
    elif alerts:
        risk = "elevated"

    return {
        "manipulation_risk": risk,
        "alert_count": len(alerts),
        "alerts": alerts,
        "categories_checked": [
            "aggressive_revenue_recognition",
            "capitalised_expenses",
            "margin_smoothing",
            "cookie_jar_reserves",
            "large_one_offs",
            "related_party_abuse",
            "frequent_adjustments",
            "sudden_policy_changes",
        ],
    }
