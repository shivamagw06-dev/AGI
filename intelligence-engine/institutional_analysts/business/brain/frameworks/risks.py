"""Framework 11 — Business Risks."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of


_CATEGORIES = (
    ("Competition", ("compet", "rival", "price")),
    ("Disruption", ("disrupt", "fintech", "technolog", "substitut")),
    ("Regulation", ("regulat", "policy", "license", "compliance")),
    ("Execution", ("execution", "operat", "underwrit")),
    ("Customer concentration", ("concentration", "single customer")),
    ("Technology", ("cyber", "tech failure", "legacy")),
    ("Labour", ("labour", "talent", "wage")),
    ("Supply chain", ("supply", "funding", "liquidity", "input")),
)


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    risks = as_list(evidence.get("business_risks"), limit=8)
    b = blob_of(risks, evidence.get("advantages"), evidence.get("business_model"))

    categorised: dict[str, str] = {}
    for label, keys in _CATEGORIES:
        matched = [r for r in risks if any(k in r.lower() for k in keys)]
        if matched:
            categorised[label] = matched[0]
        elif any(k in b for k in keys):
            categorised[label] = f"{label} pressure is a live monitoring item"
        else:
            categorised[label] = f"{label} not currently flagged as primary"

    primary = risks[:4] or [v for v in categorised.values() if "not currently" not in v][:3]
    thesis_breakers = [
        f"Permanent loss of funding / distribution advantage would undermine {name}'s economic engine.",
        "Sustained industry overcapacity or regulatory shock that compresses returns on incremental capital.",
    ]

    return {
        "framework": "Business Risks",
        "completed": bool(risks),
        "categories": categorised,
        "primary_risks": primary,
        "thesis_breakers": thesis_breakers,
        "assessment": (
            f"The ownership case for {name} weakens if {primary[0].lower() if primary else 'competitive intensity'} "
            "persistently erodes franchise returns."
        ),
        "opportunities_inverse": as_list(evidence.get("growth_opportunities"), limit=4),
    }
