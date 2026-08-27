"""Company-specific evidence seeds for framework application exams.

Institutional soft knowledge — not live market data fetches, not book quotes.
"""

from __future__ import annotations

from typing import Any

COMPANY_EVIDENCE: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "name": "HDFC Bank",
        "sector": "Banking",
        "business": {
            "franchise": "Large private-bank liability franchise with historically strong CASA",
            "moat_sources": ["deposit franchise", "underwriting culture", "distribution"],
            "moat_trajectory": "durable but no longer clearly strengthening",
            "porter": {
                "rivalry": "Intense among private banks and large PSUs for deposits and retail assets",
                "buyer_power": "Retail depositors fragmented; large wholesale depositors more powerful",
                "supplier_power": "Funding suppliers (depositors/markets) gain power when liquidity tightens",
                "substitutes": "Capital markets, NBFCs, fintech payment/lending rails",
                "entrants": "Licensing and capital raise barriers; digital disruptors pressuring distribution",
                "conclusion": "Attractive franchise economics exist, but rivalry and funding competition cap uniqueness",
            },
        },
        "financial": {
            "loan_growth": "Still growing advances, but mix and funding cost matter more than headline growth",
            "deposit_mix": "CASA advantage softer vs prior decade amid deposit competition",
            "nim": "NIM under pressure vs prior peak franchise years",
            "capital": "Capital adequacy remains a core resilience pillar",
            "asset_quality": "Credit costs manageable in base case; cycle remains the swing factor",
            "cash_earnings_note": "For banks, focus on cash-like earnings quality via credit cost and mark-to-market, not classic ROIC",
        },
        "valuation": {
            "premium_debate": "Market often awards P/B premium for franchise ROE durability",
            "key_assumptions": ["sustainable ROE", "credit costs", "deposit franchise persistence"],
            "mos_note": "Premium valuation narrows margin of safety unless earnings power is durable",
        },
        "risks": [
            "Deposit competition eroding liability advantage",
            "NIM compression",
            "Credit-cycle surprise",
            "Integration/scale complexity after merger era",
        ],
        "memory_seed": {
            "previous_opinion": "High-quality franchise with strengthening liability moat",
            "updated_opinion": "Moat remains durable; trajectory no longer clearly strengthening — vigilance on deposit mix, NIM and capital",
            "changed": ["loan growth quality", "deposit mix / CASA", "NIM", "capital deployment after scale-up"],
        },
    },
    "NESTLEIND": {
        "name": "Nestlé India",
        "sector": "FMCG",
        "business": {
            "franchise": "Premium packaged-food brand with deep distribution",
            "pricing_power": "Brand + habit + distribution support price/mix resilience",
            "moat_sources": ["brand", "distribution", "product habit"],
        },
        "financial": {
            "gross_margin": "Structurally high vs many staples peers",
            "working_capital": "Typically disciplined WC; watch inventory in inflation spikes",
            "roic": "High ROIC franchise characteristics when brand holds",
        },
        "valuation": {
            "premium_debate": "Often prices in durable growth + pricing power",
            "mos_note": "High expectations require wider MOS if volume/mix falters",
            "key_assumptions": ["volume growth", "gross margin", "rural recovery"],
        },
        "risks": ["input-cost spikes", "downtrading", "channel shift"],
    },
    "ULTRACEMCO": {
        "name": "UltraTech Cement",
        "sector": "Industrials",
        "business": {
            "capital_cycle": {
                "position": "Industry ROCE and capacity additions define mid-cycle vs peak",
                "capacity": "Large installed base; industry additions can compress pricing",
                "returns": "Returns mean-revert when capacity floods regions",
                "conclusion": "Value depends on buying mid-cycle economics, not peak utilization narrative",
            }
        },
        "financial": {"operating_leverage": "High; volume/price swings dominate earnings"},
        "valuation": {"mos_note": "Avoid peak-EPS multiples; normalize through cycle"},
        "risks": ["capacity overbuild", "fuel costs", "regional price wars"],
    },
    "TCS": {
        "name": "TCS",
        "sector": "IT Services",
        "business": {
            "franchise": "Scale IT services with large client relationships",
            "moat_sources": ["switching costs in large engagements", "delivery scale", "brand trust"],
        },
        "financial": {
            "roic": "Asset-light model supports high ROIC when utilization and pricing hold",
            "cash_conversion": "Historically strong FCF conversion of earnings",
            "growth_fcf": "Growth typically less capital-consumptive than manufacturing",
            "margins": "Margin structure sensitive to wage inflation and utilization",
            "working_capital": "Receivables/DSO and unbilled revenue are key WC tells",
        },
        "valuation": {
            "key_assumptions": ["revenue growth", "EBIT margin", "FCF conversion"],
            "implied_growth_note": "Reverse DCF should test whether priced growth exceeds plausible IT spend share",
        },
        "risks": ["client concentration", "automation", "visa/wage inflation", "USD"],
    },
    "ETERNAL": {
        "name": "Eternal",
        "sector": "Consumer Internet",
        "business": {
            "narrative": "Platform/marketplace growth narrative around users, engagement, take-rate",
            "numbers_needed": ["unit economics", "contribution margin", "cash burn / FCF path", "cohort retention"],
            "amazon_like": ["long-term platform ambition", "reinvestment narrative", "ecosystem optionality"],
            "groupon_like": ["deal/discount dependence risk", "weak retention if promotions dominate", "fragile unit economics"],
            "analogue_call": "Resembles Amazon only if cohort retention and path to FCF are evidenced; resembles Groupon if growth is promotion-led without durable unit economics",
        },
        "financial": {"unit_economics": "Must prove contribution margin and cash path"},
        "valuation": {"mos_note": "Narrative without numbers → demand wider MOS / refuse full capitalization"},
        "risks": ["multi-homing", "promotion dependency", "funding/liquidity"],
    },
    "AAPL": {
        "name": "Apple",
        "sector": "Consumer Internet / Hardware Ecosystem",
        "business": {
            "moat": ["ecosystem lock-in", "switching costs", "brand", "services attach"],
            "pricing_power": "Hardware + services pricing power conditional on ecosystem strength",
            "vs_cocacola": {
                "similar": ["brand-led pricing", "habit/identity", "global franchise"],
                "differ": ["tech ecosystem refresh cycles", "hardware dependency", "regulatory platform risk"],
                "lesson": "Pricing power is durable only while the consumption habit/ecosystem remains essential",
            },
        },
        "financial": {"roic": "High returns with strong cash generation historically"},
        "valuation": {"premium_note": "Premium justified only while ecosystem and services mix sustain returns"},
        "risks": ["ecosystem weakening", "regulation", "hardware commoditization"],
    },
    "YESBANK": {
        "name": "Yes Bank",
        "sector": "Banking",
        "business": {
            "analogue": {
                "wirecard_like": ["governance/credibility stress", "trust fracture risk"],
                "turnaround_like": ["balance-sheet cleanup path", "franchise rebuild possibility"],
                "call": "Closer to a credibility/franchise stress case than a clean cyclical turnaround unless governance and asset-quality repair are proven",
                "lesson": "Banking turnarounds fail when trust and underwriting culture do not return with capital",
            }
        },
        "risks": ["asset quality", "funding confidence", "dilution", "governance"],
    },
    "RELIANCE": {
        "name": "Reliance",
        "sector": "Conglomerate / Energy / Digital",
        "business": {
            "capital_allocation": {
                "berkshire_like": ["multi-vertical capital deployment", "optionality across platforms"],
                "ge_like": ["complexity risk", "conglomerate oversight burden", "capital intensity waves"],
                "call": "Closer to Berkshire when incremental capital earns and complexity is governed; closer to GE when complexity outruns allocation discipline",
                "lesson": "Judge the allocator by incremental returns and complexity control, not by empire scale",
            }
        },
        "risks": ["execution across verticals", "leverage/cash timing", "regulatory"],
    },
    "NOKIA": {
        "name": "Nokia",
        "sector": "Technology Hardware",
        "business": {
            "moat_loss": [
                "Failed to adapt OS/ecosystem transition",
                "App developer gravity shifted elsewhere",
                "Hardware brand could not defend against platform lock-in",
                "Creative destruction overtook product-cycle advantage",
            ]
        },
    },
    "COSTCO": {
        "name": "Costco",
        "sector": "Retail",
        "business": {
            "membership_model": [
                "Membership fee creates aligned recurring economics",
                "High retention signals customer surplus",
                "Scale purchasing reinforces price credibility",
                "Treasure-hunt assortment + trust loop strengthens switching costs",
            ]
        },
    },
}


def evidence_for(company: str | None = None, ticker: str | None = None) -> dict[str, Any]:
    keys: list[str] = []
    if ticker:
        keys.append(str(ticker).upper())
    if company:
        c = str(company).upper().strip()
        keys.append(c)
        keys.append(c.replace(" ", ""))
        # aliases
        aliases = {
            "HDFC BANK": "HDFCBANK",
            "NESTLÉ INDIA": "NESTLEIND",
            "NESTLE INDIA": "NESTLEIND",
            "ULTRATECH CEMENT": "ULTRACEMCO",
            "ULTRATECH": "ULTRACEMCO",
            "APPLE": "AAPL",
            "YES BANK": "YESBANK",
            "RELIANCE INDUSTRIES": "RELIANCE",
        }
        if c in aliases:
            keys.append(aliases[c])
    for k in keys:
        if k in COMPANY_EVIDENCE:
            return dict(COMPANY_EVIDENCE[k])
    return {}
