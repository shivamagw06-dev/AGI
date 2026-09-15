"""Framework 1 — Profitability Assessment."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, blob_of, txt, trend_label


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    revenue = txt(evidence.get("revenue"))
    margins = txt(evidence.get("margins"))
    ebitda = txt(evidence.get("ebitda"))
    ebit = txt(evidence.get("ebit"))
    net = txt(evidence.get("net_profit"))
    trend = txt(evidence.get("trend"))
    narrative = txt(evidence.get("narrative"))
    b = blob_of(revenue, margins, ebitda, ebit, net, trend, narrative)

    improving = any(k in b for k in ("improv", "expand", "accelerat", "strong"))
    weakening = any(k in b for k in ("compress", "deterior", "pressure", "declin"))
    structural = (
        "Structural — driven by mix, cost discipline or scale efficiencies rather than one-off items"
        if improving and not any(k in b for k in ("one-off", "exceptional", "temporary"))
        else "Temporary vs structural drivers still require confirmation"
        if improving
        else "Margin pressure may be cyclical or competitive — sustainability under review"
    )

    assessment = (
        f"Profitability for {name} is {trend_label(trend or narrative).lower()}. "
        + (
            "Margin and operating leverage signals suggest earnings power is expanding with the top line, "
            "which strengthens the financial support for the investment thesis."
            if improving and not weakening
            else "Margin or operating leverage signals are mixed, so stronger reported profits alone "
            "do not yet confirm durable economic value creation."
            if not weakening
            else "Weaker margin or operating leverage signals reduce confidence that reported profits "
            "translate into durable value creation."
        )
    )

    return {
        "framework": "Profitability",
        "completed": bool(revenue or margins or ebitda or ebit or net or narrative),
        "revenue": revenue or "Revenue trajectory under review",
        "gross_margin": margins or "Gross / operating margin trajectory under review",
        "ebitda_margin": ebitda or margins or "n/a",
        "ebit_margin": ebit or "n/a",
        "net_margin": net or "n/a",
        "operating_leverage": (
            "Positive operating leverage indicated when earnings outpace revenue"
            if improving
            else "Operating leverage not clearly confirmed"
        ),
        "incremental_margin": (
            "Incremental margins appear supportive"
            if improving
            else "Incremental margin quality under review"
        ),
        "margin_sustainability": structural,
        "trajectory": trend_label(trend or narrative),
        "assessment": assessment,
    }
