"""Financial validation — anomalies and mismatches (explain every flag)."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of


def run_validation(
    *,
    evidence: dict[str, Any],
    frameworks: dict[str, Any],
    executive: str,
) -> dict[str, Any]:
    flags: list[dict[str, str]] = []
    blob = blob_of(
        evidence.get("narrative"),
        evidence.get("monitors"),
        evidence.get("cash_flow"),
        evidence.get("debt"),
        evidence.get("financial_quality"),
        (frameworks.get("earnings_quality") or {}).get("assessment"),
        (frameworks.get("cash_flow") or {}).get("assessment"),
        (frameworks.get("balance_sheet") or {}).get("assessment"),
        (frameworks.get("capital_allocation") or {}).get("assessment"),
    )

    def add(kind: str, detail: str) -> None:
        flags.append({"flag": kind, "explanation": detail})

    if any(k in blob for k in ("mismatch", "accrual", "aggress")):
        add(
            "Accounting anomaly / aggressiveness watch",
            "Earnings quality language or monitoring items suggest accruals or recognition risk; "
            "cash confirmation is required before treating profits as durable.",
        )
    if (frameworks.get("cash_flow") or {}).get("cash_conversion") == "Watch":
        add(
            "Cash flow mismatch",
            "Accounting profit is not clearly converting into operating/free cash flow on present evidence.",
        )
    if any(k in blob for k in ("margin compress", "inconsist")):
        add(
            "Margin inconsistency",
            "Margin direction conflicts with growth or cost commentary; isolate mix, one-offs and operating leverage.",
        )
    if not (frameworks.get("capital_allocation") or {}).get("shareholder_value_created"):
        add(
            "Capital allocation deterioration risk",
            "Capital deployment has not yet demonstrated clear shareholder-value creation versus opportunity cost.",
        )
    if any(k in blob for k in ("stress", "high leverage", "maturity", "liquidity")) or not (
        frameworks.get("balance_sheet") or {}
    ).get("resilient"):
        add(
            "Debt / liquidity stress watch",
            "Leverage or liquidity signals reduce recession resilience and elevate refinancing risk.",
        )
    if any(k in blob for k in ("beneish", "manipul", "fraud", "wirecard")):
        add(
            "Financial manipulation signal",
            "Qualitative screens resemble known manipulation / integrity-failure patterns; elevate accounting confidence discount.",
        )
    if any(k in blob for k in ("one-off", "exceptional", "non-recurring")):
        add(
            "One-off distortion",
            "Non-recurring items may inflate or depress reported earnings; adjust for recurring earning power.",
        )

    # Domain leakage soft check
    lower = (executive or "").lower()
    for token in ("moat", "brand", "pricing power", "p/e", "intrinsic", "margin of safety", "macro", "gdp"):
        if token in lower:
            add("Out-of-mandate language", f"Financial opinion contained out-of-mandate token: {token}")

    return {
        "passed": len(flags) == 0,
        "flags": flags,
        "flag_count": len(flags),
        "explanations": [f["explanation"] for f in flags],
    }
