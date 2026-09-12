"""Company / sector forecast profile priors — institutional, not price targets."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_BANK_WEIGHTS = {
    "interest_rates": 0.85,
    "inflation": 0.45,
    "oil": 0.35,
    "currencies": 0.25,
    "gdp": 0.7,
    "bond_yields": 0.75,
    "credit_growth": 0.9,
    "commodity_prices": 0.2,
    "regulation": 0.55,
    "consumer_demand": 0.5,
}

PROFILE_PACKS: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "ticker": "HDFCBANK",
        "sector": "banks",
        "name": "HDFC Bank",
        "key_drivers": ["loan_growth", "nim", "credit_cost", "casa", "deposit_cost"],
        "market_expects": {
            "loan_growth_pct": 14.0,
            "nim_bps_change": 0,
            "credit_cost_pct": 0.55,
            "narrative": "Street expects mid-teens loan growth with stable NIM and contained credit costs",
        },
        "agib_base": {
            "loan_growth_pct": 15.0,
            "nim_bps_change": 0,
            "credit_cost_pct": 0.5,
            "narrative": "AGIB base assumes franchise loan growth slightly ahead of street with NIM stabilisation",
        },
        "sensitivity_weights": dict(_BANK_WEIGHTS),
        "analogues": [
            {"year": 2013, "similarity": 0.62, "note": "Deposit repricing / liquidity tightness episode"},
            {"year": 2018, "similarity": 0.58, "note": "NBFC stress spillover into bank funding costs"},
            {"year": 2020, "similarity": 0.55, "note": "Credit-cost uncertainty under macro shock"},
            {"year": 2022, "similarity": 0.7, "note": "Rate-hike cycle with NIM expansion then lag"},
        ],
        "catalysts": [
            {"id": "rbi_rate_cut", "label": "RBI rate cut", "polarity": "positive", "kind": "expected", "horizon": "1-3Q"},
            {"id": "guidance_revision", "label": "Guidance revision on loan growth / NIM", "polarity": "mixed", "kind": "potential", "horizon": "next print"},
            {"id": "asset_quality", "label": "Asset-quality print", "polarity": "mixed", "kind": "expected", "horizon": "quarterly"},
            {"id": "deposit_cost", "label": "Deposit-cost peak / CASA inflection", "polarity": "positive", "kind": "potential", "horizon": "2-4Q"},
            {"id": "regulatory_action", "label": "Regulatory action on unsecured / risk weights", "polarity": "negative", "kind": "unknown", "horizon": "uncertain"},
        ],
        "triggers": {
            "bull": [
                {"metric": "loan_growth", "condition": "> 15%", "observable": True},
                {"metric": "nim", "condition": "stabilises / expands", "observable": True},
                {"metric": "credit_cost", "condition": "< 0.6%", "observable": True},
            ],
            "base": [
                {"metric": "loan_growth", "condition": "12–15%", "observable": True},
                {"metric": "nim", "condition": "stable ±5 bps", "observable": True},
                {"metric": "credit_cost", "condition": "0.45–0.65%", "observable": True},
            ],
            "bear": [
                {"metric": "casa", "condition": "declines", "observable": True},
                {"metric": "deposit_cost", "condition": "rises", "observable": True},
                {"metric": "nim", "condition": "falls", "observable": True},
                {"metric": "asset_quality", "condition": "weakens", "observable": True},
            ],
            "stress": [
                {"metric": "credit_cost", "condition": "> 1.0%", "observable": True},
                {"metric": "loan_growth", "condition": "< 8%", "observable": True},
                {"metric": "systemic_funding", "condition": "tightens sharply", "observable": True},
            ],
            "recovery": [
                {"metric": "credit_cost", "condition": "normalises below 0.7%", "observable": True},
                {"metric": "loan_growth", "condition": "re-accelerates > 12%", "observable": True},
            ],
        },
    },
    "KOTAKBANK": {
        "ticker": "KOTAKBANK",
        "sector": "banks",
        "name": "Kotak Mahindra Bank",
        "key_drivers": ["loan_growth", "nim", "credit_cost", "casa"],
        "market_expects": {
            "loan_growth_pct": 13.0,
            "narrative": "Street expects quality franchise growth with regulatory / governance overhang watch",
        },
        "agib_base": {
            "loan_growth_pct": 13.5,
            "narrative": "AGIB base assumes gradual re-acceleration if liability franchise holds",
        },
        "sensitivity_weights": {
            **_BANK_WEIGHTS,
            "regulation": 0.7,
            "interest_rates": 0.82,
        },
        "analogues": [
            {"year": 2018, "similarity": 0.6, "note": "Funding / liability competition"},
            {"year": 2022, "similarity": 0.65, "note": "Rate cycle NIM dynamics"},
        ],
        "catalysts": [
            {"id": "rbi_rate_cut", "label": "RBI rate cut", "polarity": "positive", "kind": "expected", "horizon": "1-3Q"},
            {"id": "regulatory_action", "label": "Regulatory clarity", "polarity": "mixed", "kind": "potential", "horizon": "uncertain"},
            {"id": "guidance_revision", "label": "Guidance revision", "polarity": "mixed", "kind": "expected", "horizon": "next print"},
        ],
        "triggers": {
            "bull": [
                {"metric": "loan_growth", "condition": "> 15%", "observable": True},
                {"metric": "nim", "condition": "stabilises", "observable": True},
                {"metric": "credit_cost", "condition": "< 0.6%", "observable": True},
            ],
            "base": [
                {"metric": "loan_growth", "condition": "11–14%", "observable": True},
                {"metric": "nim", "condition": "stable", "observable": True},
            ],
            "bear": [
                {"metric": "casa", "condition": "declines", "observable": True},
                {"metric": "deposit_cost", "condition": "rises", "observable": True},
                {"metric": "nim", "condition": "falls", "observable": True},
            ],
            "stress": [
                {"metric": "credit_cost", "condition": "> 1.0%", "observable": True},
                {"metric": "regulatory_constraint", "condition": "tightens growth", "observable": True},
            ],
            "recovery": [
                {"metric": "loan_growth", "condition": "re-accelerates", "observable": True},
                {"metric": "credit_cost", "condition": "normalises", "observable": True},
            ],
        },
    },
    "TCS": {
        "ticker": "TCS",
        "sector": "it_services",
        "name": "Tata Consultancy Services",
        "key_drivers": ["usd", "deal_wins", "utilization", "pricing", "us_demand"],
        "market_expects": {
            "revenue_growth_cc_pct": 3.5,
            "ebit_margin_pct": 24.5,
            "narrative": "Street expects modest CC growth with stable margins and selective large-deal conversion",
        },
        "agib_base": {
            "revenue_growth_cc_pct": 4.0,
            "ebit_margin_pct": 24.8,
            "narrative": "AGIB base assumes gradual demand recovery with USD translation support and disciplined margins",
        },
        "sensitivity_weights": {
            "interest_rates": 0.35,
            "inflation": 0.3,
            "oil": 0.15,
            "currencies": 0.9,
            "gdp": 0.55,
            "bond_yields": 0.4,
            "credit_growth": 0.15,
            "commodity_prices": 0.1,
            "regulation": 0.25,
            "consumer_demand": 0.35,
        },
        "analogues": [
            {"year": 2013, "similarity": 0.5, "note": "Currency volatility with INR weakness"},
            {"year": 2018, "similarity": 0.55, "note": "Digital transition / discretionary spend caution"},
            {"year": 2020, "similarity": 0.6, "note": "Demand shock then cloud acceleration"},
            {"year": 2022, "similarity": 0.72, "note": "Post-pandemic deal slowdown and margin defence"},
        ],
        "catalysts": [
            {"id": "large_order_win", "label": "Large order / mega-deal win", "polarity": "positive", "kind": "potential", "horizon": "1-2Q"},
            {"id": "usd_move", "label": "USD strength / INR weakness", "polarity": "positive", "kind": "expected", "horizon": "ongoing"},
            {"id": "guidance_revision", "label": "Guidance revision", "polarity": "mixed", "kind": "expected", "horizon": "next print"},
            {"id": "us_budget_it", "label": "US enterprise IT budget reset", "polarity": "mixed", "kind": "potential", "horizon": "FY"},
            {"id": "management_change", "label": "Leadership transition effects", "polarity": "mixed", "kind": "unknown", "horizon": "uncertain"},
        ],
        "triggers": {
            "bull": [
                {"metric": "cc_growth", "condition": "> 6%", "observable": True},
                {"metric": "large_deals", "condition": "pipeline converts", "observable": True},
                {"metric": "ebit_margin", "condition": "stable/expanding", "observable": True},
            ],
            "base": [
                {"metric": "cc_growth", "condition": "2–5%", "observable": True},
                {"metric": "ebit_margin", "condition": "24–25.5%", "observable": True},
            ],
            "bear": [
                {"metric": "cc_growth", "condition": "< 1%", "observable": True},
                {"metric": "pricing", "condition": "pressure intensifies", "observable": True},
                {"metric": "utilization", "condition": "falls", "observable": True},
            ],
            "stress": [
                {"metric": "us_demand", "condition": "sharp discretionary freeze", "observable": True},
                {"metric": "cc_growth", "condition": "negative", "observable": True},
            ],
            "recovery": [
                {"metric": "deal_wins", "condition": "re-accelerate", "observable": True},
                {"metric": "cc_growth", "condition": "> 4%", "observable": True},
            ],
        },
    },
    "NESTLEIND": {
        "ticker": "NESTLEIND",
        "sector": "fmcg",
        "name": "Nestlé India",
        "key_drivers": ["volume_growth", "gross_margin", "rural_demand", "input_costs", "inr"],
        "market_expects": {
            "volume_growth_pct": 5.0,
            "gross_margin_trend": "stable",
            "narrative": "Street expects mid-single-digit volumes with gradual rural recovery and manageable commodity costs",
        },
        "agib_base": {
            "volume_growth_pct": 5.5,
            "gross_margin_trend": "mild expansion if oil/agri ease",
            "narrative": "AGIB base leans on premium mix and rural heal with imported-inflation watch",
        },
        "sensitivity_weights": {
            "interest_rates": 0.3,
            "inflation": 0.8,
            "oil": 0.7,
            "currencies": 0.65,
            "gdp": 0.6,
            "bond_yields": 0.25,
            "credit_growth": 0.2,
            "commodity_prices": 0.85,
            "regulation": 0.35,
            "consumer_demand": 0.9,
        },
        "analogues": [
            {"year": 2013, "similarity": 0.68, "note": "INR weakness / imported inflation pressure"},
            {"year": 2018, "similarity": 0.52, "note": "Rural demand soft patch"},
            {"year": 2020, "similarity": 0.48, "note": "Consumption mix shift under shock"},
            {"year": 2022, "similarity": 0.66, "note": "Commodity-cost inflation into FMCG margins"},
        ],
        "catalysts": [
            {"id": "oil_decline", "label": "Sustained oil / agri cost decline", "polarity": "positive", "kind": "potential", "horizon": "2-4Q"},
            {"id": "budget", "label": "Union Budget consumption measures", "polarity": "positive", "kind": "expected", "horizon": "annual"},
            {"id": "rural_recovery", "label": "Rural demand recovery prints", "polarity": "positive", "kind": "expected", "horizon": "1-3Q"},
            {"id": "rupee_weakness", "label": "Rupee weakness shock", "polarity": "negative", "kind": "potential", "horizon": "ongoing"},
            {"id": "election", "label": "Election-related consumption pulse", "polarity": "mixed", "kind": "potential", "horizon": "cycle"},
        ],
        "triggers": {
            "bull": [
                {"metric": "volume_growth", "condition": "> 7%", "observable": True},
                {"metric": "gross_margin", "condition": "expands", "observable": True},
                {"metric": "rural_demand", "condition": "re-accelerates", "observable": True},
            ],
            "base": [
                {"metric": "volume_growth", "condition": "4–6%", "observable": True},
                {"metric": "gross_margin", "condition": "stable", "observable": True},
            ],
            "bear": [
                {"metric": "input_costs", "condition": "rise sharply", "observable": True},
                {"metric": "volume_growth", "condition": "< 3%", "observable": True},
                {"metric": "inr", "condition": "weakens materially", "observable": True},
            ],
            "stress": [
                {"metric": "consumer_demand", "condition": "contracts", "observable": True},
                {"metric": "gross_margin", "condition": "compresses hard", "observable": True},
            ],
            "recovery": [
                {"metric": "volume_growth", "condition": "returns > 5%", "observable": True},
                {"metric": "input_costs", "condition": "normalise", "observable": True},
            ],
        },
    },
    "TATASTEEL": {
        "ticker": "TATASTEEL",
        "sector": "metals",
        "name": "Tata Steel",
        "key_drivers": ["steel_spread", "china_demand", "coking_coal", "europe_ops", "volumes"],
        "market_expects": {
            "spread_trend": "stable-to-soft",
            "narrative": "Street expects China-linked steel prices and Europe profitability as swing factors",
        },
        "agib_base": {
            "spread_trend": "range-bound with China downside risk",
            "narrative": "AGIB base assumes no hard China landing but elevated commodity cyclicality",
        },
        "sensitivity_weights": {
            "interest_rates": 0.4,
            "inflation": 0.35,
            "oil": 0.45,
            "currencies": 0.4,
            "gdp": 0.55,
            "bond_yields": 0.35,
            "credit_growth": 0.3,
            "commodity_prices": 0.95,
            "regulation": 0.4,
            "consumer_demand": 0.35,
        },
        "analogues": [
            {"year": 2013, "similarity": 0.55, "note": "Global steel soft patch"},
            {"year": 2018, "similarity": 0.6, "note": "Trade / China demand swings"},
            {"year": 2020, "similarity": 0.65, "note": "Shock then commodity rebound"},
            {"year": 2022, "similarity": 0.7, "note": "Energy-cost and Europe margin stress"},
        ],
        "catalysts": [
            {"id": "china_stimulus", "label": "China stimulus / demand pulse", "polarity": "positive", "kind": "potential", "horizon": "1-3Q"},
            {"id": "steel_price", "label": "Steel price / spread move", "polarity": "mixed", "kind": "expected", "horizon": "ongoing"},
            {"id": "oil_shock", "label": "Energy / oil shock", "polarity": "negative", "kind": "potential", "horizon": "uncertain"},
            {"id": "regulatory_action", "label": "Export / carbon regulation", "polarity": "negative", "kind": "unknown", "horizon": "uncertain"},
        ],
        "triggers": {
            "bull": [
                {"metric": "steel_spread", "condition": "expands", "observable": True},
                {"metric": "china_demand", "condition": "improves", "observable": True},
            ],
            "base": [
                {"metric": "steel_spread", "condition": "range-bound", "observable": True},
                {"metric": "volumes", "condition": "stable", "observable": True},
            ],
            "bear": [
                {"metric": "china_demand", "condition": "weakens", "observable": True},
                {"metric": "coking_coal", "condition": "spikes", "observable": True},
            ],
            "stress": [
                {"metric": "europe_ops", "condition": "deep losses", "observable": True},
                {"metric": "steel_spread", "condition": "collapses", "observable": True},
            ],
            "recovery": [
                {"metric": "spreads", "condition": "normalise", "observable": True},
                {"metric": "china_demand", "condition": "stabilises", "observable": True},
            ],
        },
    },
}


def profile_for(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND", "TATA": "TATASTEEL"}
    t = aliases.get(t, t)
    pack = PROFILE_PACKS.get(t)
    return deepcopy(pack) if pack else None


def list_profiles() -> list[str]:
    return sorted(PROFILE_PACKS.keys())
