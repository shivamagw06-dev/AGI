"""Valuation DNA — permanent valuation profile."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain._text import parse_num, txt


def build_dna(
    *,
    company: str,
    ticker: str | None,
    evidence: dict[str, Any],
    frameworks: dict[str, Any],
    prior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pe = parse_num(evidence.get("pe") or evidence.get("forward_pe"))
    mos = txt(evidence.get("margin_of_safety")).lower()
    band = str((frameworks.get("market_expectations") or {}).get("premium_or_discount") or "")
    hist = str((frameworks.get("historical_valuation") or {}).get("current_vs_history") or "")

    if "Depressed" in hist or any(w in mos for w in ("high", "wide", "ample")):
        profile = "Deep Value" if pe is not None and pe <= 12 else "Fairly Valued Compounder"
    elif "Rich" in hist or "Premium" in band or (pe is not None and pe >= 28):
        profile = "Premium Compounder" if pe is not None and pe < 45 else "High Growth / Speculative"
    elif pe is not None and pe >= 22:
        profile = "Premium Compounder"
    else:
        profile = "Fairly Valued Compounder"

    if "cyclical" in blob_safe(evidence):
        profile = "Cyclical"
    if "turnaround" in blob_safe(evidence):
        profile = "Turnaround"
    if "asset" in blob_safe(evidence) and "rich" in blob_safe(evidence):
        profile = "Asset Rich"

    dna = {
        "company": company,
        "ticker": (ticker or "").upper() or None,
        "profile": profile,
        "premium_or_discount": band or "Fair / mixed cushion",
        "historical_band": hist or "n/a",
        "expectation_intensity": "Demanding" if "Premium" in band else "Moderate",
        "margin_of_safety_character": (frameworks.get("margin_of_safety") or {}).get("downside_protection"),
        "updated_from_prior": bool(prior),
    }
    changes = []
    if prior and prior.get("profile") and prior.get("profile") != profile:
        changes.append(f"profile: {prior.get('profile')} → {profile}")
    dna["dna_changes"] = changes
    dna["summary"] = (
        f"{company} valuation DNA — {profile}; expectations {dna['expectation_intensity'].lower()}; "
        f"cushion {str(dna['margin_of_safety_character'] or 'mixed').lower()}."
    )
    return dna


def blob_safe(evidence: dict[str, Any]) -> str:
    return " ".join(str(v).lower() for v in evidence.values() if not isinstance(v, (dict, list)))
