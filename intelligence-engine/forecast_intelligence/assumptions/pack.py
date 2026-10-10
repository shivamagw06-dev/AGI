"""Scenario assumption packs by sector."""

from __future__ import annotations

from typing import Any

_SECTOR_ASSUMPTIONS: dict[str, dict[str, dict[str, Any]]] = {
    "banks": {
        "bull": {
            "macro": "Orderly rate cuts, healthy credit demand",
            "business": "Loan growth >15%, CASA resilient",
            "financial": "NIM stable/expanding, credit cost <0.6%",
            "valuation": "Multiple supported by ROE expansion",
        },
        "base": {
            "macro": "Soft landing, gradual policy easing",
            "business": "Mid-teens loan growth, competitive deposits",
            "financial": "NIM stable ±5 bps, credit cost contained",
            "valuation": "Fair multiple vs growth/ROE",
        },
        "bear": {
            "macro": "Sticky inflation, delayed cuts",
            "business": "CASA decline, slower credit",
            "financial": "NIM compression, rising credit cost",
            "valuation": "Multiple compression on ROE risk",
        },
        "stress": {
            "macro": "Hard landing / funding shock",
            "business": "Credit freeze, liability stress",
            "financial": "Credit cost >1%, sharp NIM fall",
            "valuation": "Deep de-rating under systemic risk",
        },
        "recovery": {
            "macro": "Policy support after stress",
            "business": "Credit re-acceleration",
            "financial": "Credit cost normalises, NIM repairs",
            "valuation": "Partial multiple recovery",
        },
    },
    "it_services": {
        "bull": {
            "macro": "US demand heal + supportive USD",
            "business": "Large-deal conversion, utilization up",
            "financial": "CC growth >6%, margins stable/up",
            "valuation": "Growth re-rating",
        },
        "base": {
            "macro": "Gradual demand recovery",
            "business": "Selective deals, pricing discipline",
            "financial": "CC growth 2–5%, margins defended",
            "valuation": "Range-bound vs peers",
        },
        "bear": {
            "macro": "US discretionary freeze",
            "business": "Deal delays, utilization down",
            "financial": "CC growth <1%, margin pressure",
            "valuation": "De-rating on growth miss",
        },
        "stress": {
            "macro": "Deep US recession",
            "business": "Pipeline stalls",
            "financial": "Negative CC growth",
            "valuation": "Severe multiple compression",
        },
        "recovery": {
            "macro": "Enterprise budgets reopen",
            "business": "Deal wins re-accelerate",
            "financial": "CC growth returns >4%",
            "valuation": "Partial re-rating",
        },
    },
    "fmcg": {
        "bull": {
            "macro": "Inflation eases, rural heal",
            "business": "Volume >7%, mix premiumisation",
            "financial": "Gross margin expands",
            "valuation": "Quality premium holds/expands",
        },
        "base": {
            "macro": "Inflation moderating",
            "business": "Volumes 4–6%",
            "financial": "Margins stable",
            "valuation": "Premium justified by durability",
        },
        "bear": {
            "macro": "Imported inflation / weak INR",
            "business": "Volume slowdown",
            "financial": "Margin compression",
            "valuation": "Premium compresses",
        },
        "stress": {
            "macro": "Demand contraction",
            "business": "Volumes stall",
            "financial": "Hard margin hit",
            "valuation": "Defensive de-rating",
        },
        "recovery": {
            "macro": "Costs normalise",
            "business": "Volumes return >5%",
            "financial": "Margins repair",
            "valuation": "Premium rebuilds",
        },
    },
    "metals": {
        "bull": {
            "macro": "China demand pulse",
            "business": "Spreads expand, volumes firm",
            "financial": "EBITDA upside",
            "valuation": "Cyclical re-rating",
        },
        "base": {
            "macro": "Range-bound China/steel",
            "business": "Stable volumes",
            "financial": "Mid-cycle earnings",
            "valuation": "Cycle-neutral multiple",
        },
        "bear": {
            "macro": "China slowdown",
            "business": "Spread squeeze",
            "financial": "Earnings downside",
            "valuation": "Cyclical de-rating",
        },
        "stress": {
            "macro": "Global industrial recession",
            "business": "Europe deep losses",
            "financial": "Cash-flow stress",
            "valuation": "Deep cyclical trough",
        },
        "recovery": {
            "macro": "Demand stabilises",
            "business": "Spreads normalise",
            "financial": "Earnings repair",
            "valuation": "Trough-to-mid recovery",
        },
    },
}


def assumptions_for(sector: str, scenario: str) -> dict[str, Any]:
    sec = (sector or "banks").lower()
    pack = _SECTOR_ASSUMPTIONS.get(sec) or _SECTOR_ASSUMPTIONS["banks"]
    return dict(pack.get(scenario) or pack["base"])
