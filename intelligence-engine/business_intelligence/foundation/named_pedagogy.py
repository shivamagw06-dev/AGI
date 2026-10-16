"""Named-company / archetype pedagogy for BI Foundation.

Deterministic, non-numeric institutional framing for well-known global and
Indian names where CapIQ coverage is thin or absent. This is NOT a new
Industry Intelligence phase — it enriches existing BI templates only.
"""

from __future__ import annotations

import re
from typing import Any, Optional

NAMED_PEDAGOGY: dict[str, dict[str, Any]] = {
    "ferrari": {
        "archetype": "luxury_auto",
        "industry_key": "manufacturing",
        "business_type": "manufacturer",
        "how_it_makes_money": (
            "Ferrari is a luxury auto franchise: it earns on scarcity, brand, and "
            "pricing power — deliberately low volume, high ASP, and controlled "
            "allocation rather than mass-market unit growth."
        ),
        "moats": ["brand", "scarcity", "pricing_power"],
        "contrast_keys": {
            "pricing": "scarcity + brand + low volume / high ASP",
            "volume": "intentionally constrained luxury volume",
            "margin_driver": "pricing power and mix, not scale",
        },
    },
    "toyota": {
        "archetype": "mass_market_auto",
        "industry_key": "manufacturing",
        "business_type": "manufacturer",
        "how_it_makes_money": (
            "Toyota is a mass-market auto franchise: it earns on scale, cost "
            "leadership, reliability, and high volume across a broad vehicle mix — "
            "thinner unit margins than luxury, compensated by throughput."
        ),
        "moats": ["scale", "cost_leadership", "brand"],
        "contrast_keys": {
            "pricing": "competitive mass-market pricing",
            "volume": "high volume / global scale",
            "margin_driver": "cost discipline and utilization at scale",
        },
    },
    "costco": {
        "archetype": "membership_retail",
        "industry_key": "retail",
        "business_type": "retail",
        "how_it_makes_money": (
            "Costco's membership model monetises annual fees while running "
            "merchandise near pass-through / low margin: membership income funds "
            "the profit pool; volume and scale keep prices sharp and renewals high."
        ),
        "moats": ["scale", "membership_renewal", "cost_leadership"],
    },
    "apple": {
        "archetype": "platform_premium",
        "industry_key": "platform",
        "business_type": "platform",
        "how_it_makes_money": (
            "Apple sustains premium pricing through brand, ecosystem lock-in, and "
            "integrated hardware-software platforms — switching costs and perceived "
            "differentiation support ASP discipline."
        ),
        "moats": ["brand", "switching_costs", "ecosystem", "network_effects"],
    },
    "reliance": {
        "archetype": "india_conglomerate",
        "industry_key": "conglomerate",
        "business_type": "conglomerate",
        "ticker": "RELIANCE",
        "how_it_makes_money": (
            "Reliance Industries is a multi-engine Indian conglomerate: O2C "
            "(oil-to-chemicals) refining and petrochemicals generate the industrial "
            "cash engine; Jio monetises digital/telecom subscribers and connectivity; "
            "Reliance Retail scales consumer distribution; New Energy is a longer-dated "
            "optional growth segment."
        ),
        "segments": [
            "O2C / refining & petrochemicals",
            "Jio digital / telecom",
            "Reliance Retail",
            "New Energy",
        ],
        "moats": ["scale", "integration", "distribution", "digital_network"],
    },
    "visa": {
        "archetype": "payment_network",
        "industry_key": "platform",
        "business_type": "platform",
        "how_it_makes_money": (
            "Visa is an asset-light payment network: it earns a toll / transaction fee "
            "on card volume without carrying consumer credit risk, so incremental "
            "transactions convert heavily to free cash flow with limited capex."
        ),
        "moats": ["network_effects", "brand", "switching_costs"],
        "contrast_keys": {
            "pricing": "network toll on card volume",
            "volume": "global acceptance footprint",
            "margin_driver": "asset-light take-rate and scale",
        },
    },
    "mastercard": {
        "archetype": "payment_network",
        "industry_key": "platform",
        "business_type": "platform",
        "how_it_makes_money": (
            "Mastercard is an asset-light payment network similar to Visa: it earns "
            "on transaction and service fees across its acceptance network without "
            "funding consumer credit balances, so economics centre on take-rate, "
            "volume mix, and network density."
        ),
        "moats": ["network_effects", "brand", "switching_costs"],
        "contrast_keys": {
            "pricing": "network toll and value-added services",
            "volume": "global acceptance and cross-border mix",
            "margin_driver": "asset-light fee economics",
        },
    },
}

_ALIAS_TO_KEY: dict[str, str] = {
    "ferrari": "ferrari",
    "toyota": "toyota",
    "costco": "costco",
    "apple": "apple",
    "reliance": "reliance",
    "reliance industries": "reliance",
    "reliance industries limited": "reliance",
    "ril": "reliance",
    "visa": "visa",
    "mastercard": "mastercard",
    "master card": "mastercard",
}


def lookup_named_pedagogy(
    *,
    name: Optional[str] = None,
    ticker: Optional[str] = None,
    question: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if ticker and str(ticker).upper() == "RELIANCE":
        return dict(NAMED_PEDAGOGY["reliance"])
    candidates = []
    for raw in (name, ticker, question):
        if not raw:
            continue
        low = re.sub(r"\s+", " ", str(raw).strip().lower())
        candidates.append(low)
        for alias, key in _ALIAS_TO_KEY.items():
            if alias == low or re.search(rf"\b{re.escape(alias)}\b", low):
                return dict(NAMED_PEDAGOGY[key])
    return None


def profitability_contrast_summary(a_name: str, b_name: str, a_ped: dict[str, Any], b_ped: dict[str, Any]) -> str:
    a_keys = a_ped.get("contrast_keys") or {}
    b_keys = b_ped.get("contrast_keys") or {}
    return (
        f"{a_name} earns higher margins than {b_name} because it is a luxury scarcity "
        f"franchise with pricing power and deliberately low volume, while {b_name} is a "
        f"mass-market scale business competing on volume and cost leadership. "
        f"{a_name}: {a_keys.get('pricing', a_ped.get('archetype'))}; "
        f"{b_name}: {b_keys.get('pricing', b_ped.get('archetype'))}. "
        "Industry economics only — not company-specific audited financials."
    )
