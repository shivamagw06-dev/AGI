"""Accounting Behaviour Engine — longitudinal fingerprint (V1).

Classifies long-term operating accounting style from accumulating evidence:
Conservative / Neutral / Aggressive / Improving / Deteriorating /
Highly Predictable / Earnings Management Risk /
Conservative and Consistent / Increasingly Aggressive
"""

from __future__ import annotations

from typing import Any


def classify_behaviour(
    *,
    priors: list[str] | None,
    cash: dict[str, Any],
    earnings: dict[str, Any],
    accruals: dict[str, Any],
    policies: dict[str, Any],
    forensic: dict[str, Any],
    manipulation: dict[str, Any],
    working_capital: dict[str, Any],
) -> dict[str, Any]:
    votes: dict[str, float] = {}

    def add(label: str, w: float = 1.0) -> None:
        votes[label] = votes.get(label, 0.0) + w

    for p in priors or []:
        add(str(p), 1.2)

    if float(cash.get("cash_quality") or 0) >= 80 and float(earnings.get("earnings_quality") or 0) >= 75:
        add("Conservative", 1.5)
        add("Conservative and Consistent", 1.3)
    if accruals.get("label") == "Healthy" and policies.get("material_count", 0) == 0:
        add("Highly Predictable", 1.2)
        add("Conservative", 0.8)
    if accruals.get("label") == "Aggressive" or manipulation.get("manipulation_risk") == "high":
        add("Aggressive", 2.0)
        add("Earnings Management Risk", 1.8)
        add("Increasingly Aggressive", 1.5)
    if (forensic.get("beneish") or {}).get("beneish_risk") == "elevated":
        add("Earnings Management Risk", 1.5)
        add("Aggressive", 1.0)

    cash_signal = str(cash.get("cash_signal") or "")
    wc_signal = str(working_capital.get("efficiency_signal") or "")
    if cash_signal == "cash_improvement" or wc_signal == "efficiency_improvement":
        add("Improving", 1.4)
    if cash_signal == "cash_deterioration" or wc_signal == "efficiency_deterioration":
        add("Deteriorating", 1.3)
        # Funding/WC deterioration alone is not necessarily aggressive accounting
        add("Neutral", 0.5)

    if not votes:
        add("Neutral", 1.0)

    ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    primary = ranked[0][0]
    secondary = [k for k, _ in ranked[1:4] if k != primary]

    narrative = (
        f"Accounting behaviour classified as **{primary}** based on cash quality "
        f"{cash.get('cash_quality')}, earnings quality {earnings.get('earnings_quality')}, "
        f"accruals {accruals.get('label')}, and forensic/manipulation signals."
    )
    if primary in {"Conservative and Consistent", "Conservative", "Highly Predictable"}:
        narrative += (
            " Evidence supports conservative recognition, stable cash conversion relative to "
            "reported earnings, and low accrual / policy volatility."
        )
    elif primary in {"Increasingly Aggressive", "Aggressive", "Earnings Management Risk"}:
        narrative += (
            " Accruals, adjustments, or forensic indicators warrant enhanced committee scrutiny."
        )

    return {
        "primary": primary,
        "secondary": secondary,
        "votes": {k: round(v, 2) for k, v in ranked},
        "narrative": narrative,
        "evolves_with_evidence": True,
    }
