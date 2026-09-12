"""Financial DNA — permanent financial fingerprint."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, txt


def build_dna(
    *,
    company: str,
    ticker: str | None,
    evidence: dict[str, Any],
    frameworks: dict[str, Any],
    prior_dna: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profit = frameworks.get("profitability") or {}
    cash = frameworks.get("cash_flow") or {}
    bs = frameworks.get("balance_sheet") or {}
    rets = frameworks.get("returns") or {}
    capital = frameworks.get("capital_allocation") or {}
    durable = frameworks.get("durability") or {}
    b = blob_of(evidence.get("business_model_finance"), evidence.get("narrative"), cash.get("assessment"))

    dna = {
        "company": company,
        "ticker": (ticker or "").upper() or None,
        "revenue_model": txt(evidence.get("revenue")) or "Revenue trajectory fingerprint",
        "margin_profile": profit.get("trajectory") or "Mixed",
        "cash_generation": cash.get("cash_conversion") or "Mixed",
        "capital_intensity": (
            "Lower" if any(k in b for k in ("asset-light", "fee", "software", "services")) else "Mixed/Higher"
        ),
        "working_capital": cash.get("working_capital") or evidence.get("working_capital") or "Under review",
        "leverage": bs.get("leverage") or evidence.get("debt") or "Under review",
        "capital_allocation": capital.get("assessment") or evidence.get("capital_allocation") or "Under review",
        "financial_durability": durable.get("resilience") or "Mixed",
        "return_profile": "Attractive" if rets.get("attractive") else "Adequate/Watch",
        "updated_from_prior": bool(prior_dna),
    }
    changes = []
    if prior_dna:
        for key in (
            "margin_profile",
            "cash_generation",
            "leverage",
            "financial_durability",
            "return_profile",
        ):
            if prior_dna.get(key) and dna.get(key) and str(prior_dna.get(key)) != str(dna.get(key)):
                changes.append(f"{key}: {prior_dna.get(key)} → {dna.get(key)}")
    dna["dna_changes"] = changes[:8]
    dna["summary"] = (
        f"{company} financial DNA — margins {dna['margin_profile']}, cash {dna['cash_generation']}, "
        f"returns {dna['return_profile']}, leverage watch {dna['leverage']}, durability {dna['financial_durability']}."
    )
    return dna
