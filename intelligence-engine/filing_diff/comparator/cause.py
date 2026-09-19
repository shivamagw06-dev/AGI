"""Cause engine — what / why / drivers / implications."""

from __future__ import annotations

from typing import Any


def explain_change(
    *,
    metric: str,
    change_type: str,
    previous: Any,
    current: Any,
    previous_period: str,
    current_period: str,
) -> dict[str, Any]:
    what = f"{metric} moved from {previous} ({previous_period}) to {current} ({current_period}) [{change_type}]."
    drivers: list[str] = []
    implications: list[str] = []
    why = "Change observed across consecutive filing periods."

    if metric == "NIM":
        why = "NIM compression typically reflects funding-cost pressure and/or asset-yield lag."
        drivers = ["deposit mix shift to term deposits", "competitive deposit pricing", "rate-cycle lag"]
        implications = ["near-term NII trajectory", "liability franchise quality", "earnings expectation reset"]
    elif metric == "CASA":
        why = "CASA decline indicates funding-mix deterioration versus prior filing mix."
        drivers = ["time-deposit growth outpacing CASA", "franchise liability rebuild unfinished"]
        implications = ["cost of funds", "structural NIM path", "peer relative funding advantage"]
    elif metric == "CET1":
        why = "Capital ratio change reflects earnings retention, RWA growth, and capital actions."
        drivers = ["loan growth", "profit retention", "capital allocation choices"]
        implications = ["balance-sheet resilience", "capacity for growth / distributions"]
    elif metric == "Guidance_Status":
        why = f"Management guidance stance changed: {previous} → {current}."
        drivers = ["demand visibility", "margin outlook", "management confidence"]
        implications = ["expectation path for forward estimates", "committee monitoring intensity"]
    elif change_type.startswith("risk_"):
        why = "Risk register composition changed versus prior filing."
        drivers = ["new disclosures", "management emphasis shift"]
        implications = ["risk monitoring priority", "scenario analysis inputs"]
    elif metric.startswith("Optimism") or "outlook" in change_type:
        why = "Management tone/outlook language shifted versus prior filing."
        drivers = ["operating conditions", "funding/margin pressure acknowledgement"]
        implications = ["qualitative thesis confidence", "guidance credibility"]
    elif "dividend" in change_type or "buyback" in change_type or "capex" in change_type:
        why = "Capital allocation action set changed versus prior filing."
        drivers = ["capital buffer policy", "growth opportunities", "shareholder distribution policy"]
        implications = ["FCF use", "leverage path", "return of capital"]

    return {
        "what_changed": what,
        "why_changed": why,
        "drivers": drivers,
        "implications": implications,
        "open_questions": [
            f"Is the {metric} move structural or cyclical?",
            "Does peer trajectory confirm idiosyncratic vs sector-wide change?",
        ],
    }
