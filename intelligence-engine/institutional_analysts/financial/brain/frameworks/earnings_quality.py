"""Framework 4 — Earnings Quality."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    quality = txt(evidence.get("financial_quality") or evidence.get("quality"))
    cash = txt(evidence.get("cash_flow"))
    narrative = txt(evidence.get("narrative"))
    monitors = as_list(evidence.get("monitors"), limit=6)
    dvc = as_list(evidence.get("validation_checks"), limit=6)
    b = blob_of(quality, cash, narrative, monitors, dvc)

    trusted = any(k in b for k in ("high quality", "clean", "recurring", "strong", "validated", "cash conversion"))
    caution = any(k in b for k in ("accrual", "one-off", "aggressive", "mismatch", "manipulation", "beneish", "sloan"))
    recurring = "Recurring earnings character supported" if trusted and not caution else "Recurring vs one-off mix under review"

    assessment = (
        f"Reported earnings for {name} "
        + (
            "can be treated as relatively trustworthy on present evidence because cash conversion and "
            "quality signals align with accounting profit."
            if trusted and not caution
            else "require caution — quality screens or monitoring items suggest accruals, one-offs or "
            "conversion gaps that may overstate durable earning power."
            if caution
            else "are mixed in quality; trust rises only if cash conversion and multi-year recurrence hold."
        )
    )

    return {
        "framework": "Earnings Quality",
        "completed": bool(quality or cash or narrative or dvc),
        "sloan_accrual_ratio": "Accrual intensity inferred from cash vs earnings alignment (qualitative)",
        "piotroski_f_score": "Piotroski-style fundamentals: profitability, leverage, operating efficiency signals reviewed qualitatively",
        "beneish_m_score": "Manipulation-risk lens applied qualitatively via aggressiveness / anomaly flags",
        "quality_of_earnings": quality or ("Higher" if trusted else "Mixed"),
        "recurring_earnings": recurring,
        "one_off_items": "One-off distortions flagged for isolation" if "one-off" in b or "exceptional" in b else "No material one-offs identified in file",
        "accounting_aggressiveness": "Elevated watch" if caution else "Not elevated on present signals",
        "trusted": trusted and not caution,
        "assessment": assessment,
    }
