"""Framework 2 — Competitive Advantage / Moat."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, rate_from_signals, txt


_MOAT_DIMS = (
    ("Brand", ("brand", "trust", "franchise", "reputation")),
    ("Network effects", ("network", "ecosystem", "platform")),
    ("Switching costs", ("switch", "retention", "sticky", "lock-in", "casa")),
    ("Scale", ("scale", "size", "market share")),
    ("Distribution", ("distribution", "branch", "reach", "channel")),
    ("Technology", ("technology", "tech", "data", "digital")),
    ("Cost advantage", ("cost advantage", "low-cost", "funding cost", "operating cost")),
    ("Patents", ("patent", "ip ", "intellectual")),
    ("Regulation", ("license", "regulatory barrier", "banking license")),
    ("Relationships", ("relationship", "customer trust", "institutional")),
)


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    advantages = as_list(evidence.get("advantages"), limit=6)
    brand = txt(evidence.get("brand"))
    pricing = txt(evidence.get("pricing_power"))
    position = txt(evidence.get("competitive_position"))
    model = txt(evidence.get("business_model"))
    score = evidence.get("business_quality_score")
    b = blob_of(advantages, brand, pricing, position, model)

    dimensions: dict[str, str] = {}
    strong_hits = 0
    for label, keys in _MOAT_DIMS:
        hits = sum(1 for k in keys if k in b)
        if hits >= 2 or (hits == 1 and label in {"Brand", "Distribution", "Scale", "Switching costs", "Cost advantage"}):
            rating = "Strong"
            strong_hits += 1
        elif hits == 1:
            rating = "Medium"
        else:
            rating = "Weak"
        dimensions[label] = rating

    improving = bool(score is not None and float(score) >= 65) or strong_hits >= 3
    declining = bool(score is not None and float(score) < 45)
    durability = rate_from_signals(strong_hits, improving=improving and not declining, declining=declining)
    if durability == "Improving" and strong_hits >= 3:
        durability = "Strong"
    if improving and strong_hits >= 2 and durability == "Medium":
        durability = "Improving"

    primary = [k for k, v in dimensions.items() if v in {"Strong", "Medium", "Improving"}][:4]
    if not primary:
        primary = advantages[:3] or ["Franchise durability under review"]

    why = (
        f"{name}'s competitive advantage is primarily derived from "
        + ", ".join(primary[:3]).lower()
        + (
            ". These characteristics historically support returns above the opportunity cost of capital "
            "when execution remains disciplined."
            if durability in {"Strong", "Improving", "Medium"}
            else ". On present evidence, structural barriers are not yet clear enough to support an exceptional ownership case."
        )
    )

    return {
        "framework": "Competitive Advantage",
        "completed": True,
        "dimensions": dimensions,
        "sources": primary,
        "durability": durability,
        "trajectory": "Improving" if improving and not declining else ("Declining" if declining else "Stable"),
        "replicability": (
            "Difficult for competitors to copy quickly where brand, distribution and switching frictions reinforce each other."
            if durability in {"Strong", "Improving", "Medium"}
            else "Advantage may be contested without clearer structural barriers."
        ),
        "why_competitors_cannot_copy": (
            f"Replication is constrained because {', '.join(primary[:2]).lower() or 'franchise advantages'} "
            "compound over time and are costly to rebuild from scratch."
        ),
        "assessment": why,
        "summary": why,
    }
