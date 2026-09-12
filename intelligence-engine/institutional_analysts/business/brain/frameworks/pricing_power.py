"""Framework 7 — Pricing Power."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    pricing = txt(evidence.get("pricing_power"))
    brand = txt(evidence.get("brand"))
    advantages = as_list(evidence.get("advantages"), limit=5)
    b = blob_of(pricing, brand, advantages, evidence.get("business_model"))

    can_raise = any(k in b for k in ("pricing power", "price", "nim", "fee", "brand", "franchise", "low-cost"))
    evidence_bits = []
    if pricing:
        evidence_bits.append(pricing)
    if any(k in b for k in ("brand", "trust", "franchise")):
        evidence_bits.append("Brand / trust supports willingness to pay")
    if any(k in b for k in ("low-cost", "funding", "deposit", "scale")):
        evidence_bits.append("Cost advantage creates room to protect net pricing through the cycle")
    if not evidence_bits:
        evidence_bits = ["Pricing power not yet evidenced beyond general franchise claims"]

    assessment = (
        f"{name} can defend and selectively raise effective prices when differentiation and switching frictions "
        f"hold — supported by {evidence_bits[0].rstrip('.')}. Frequency of increases depends on competitive intensity "
        "and regulation, but customer loss should remain limited if relationship value stays high."
        if can_raise
        else f"{name}'s ability to raise prices without losing customers is not yet clearly evidenced; "
        "ownership conviction on pricing power remains provisional."
    )

    return {
        "framework": "Pricing Power",
        "completed": bool(pricing) or can_raise,
        "can_raise_prices": can_raise,
        "how_often": "Selectively through the cycle — not mechanically every period",
        "without_losing_customers": can_raise,
        "evidence": evidence_bits[:4],
        "assessment": assessment,
    }
