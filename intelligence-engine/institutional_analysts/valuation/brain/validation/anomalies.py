"""Valuation validation — expectation and multiple risks."""

from __future__ import annotations

from typing import Any


def run_validation(*, evidence: dict[str, Any], frameworks: dict[str, Any], executive: str) -> dict[str, Any]:
    flags: list[dict[str, str]] = []
    exp = frameworks.get("market_expectations") or {}
    mos = frameworks.get("margin_of_safety") or {}
    rev = frameworks.get("reverse_dcf") or {}
    premium = "Premium" in str(exp.get("premium_or_discount") or "")

    def add(kind: str, detail: str) -> None:
        flags.append({"flag": kind, "explanation": detail})

    if premium:
        add(
            "Unrealistic / demanding market expectations risk",
            "Price appears to embed above-average growth and capital-efficiency persistence; disappointment risk is elevated.",
        )
        add(
            "Multiple compression risk",
            "If delivery undershoots embedded expectations, the multiple can compress in addition to earnings risk.",
        )
        add(
            "Growth dependency",
            str(rev.get("growth_required") or "Valuation depends on delivering material growth."),
        )
        add(
            "Margin dependency",
            str(rev.get("margin_expansion_required") or "Margin durability is part of the embedded case."),
        )
    else:
        add(
            "Multiple expansion not required",
            "Base-case attractiveness depends more on cash-flow delivery than on re-rating.",
        )

    if str(mos.get("downside_protection") or "") == "Thinner":
        add(
            "Limited downside protection",
            "Margin of safety is thinner; execution risk is therefore valuation-relevant.",
        )

    add(
        "Capital allocation dependency",
        "Long-term intrinsic value still depends on whether incremental capital earns adequate returns — assessed via cash-flow assumptions, not storytelling.",
    )

    lower = (executive or "").lower()
    for token in ("moat", "brand strength", "management quality", "governance", "promoter", "momentum", "the stock is expensive", "the stock is cheap"):
        if token in lower:
            add("Out-of-mandate or lazy valuation language", f"Detected: {token}")

    return {"passed": len([f for f in flags if f["flag"].startswith("Out-of")]) == 0, "flags": flags, "flag_count": len(flags)}
