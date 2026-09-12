"""Deterministic hypothesis catalog v1.0.0 — no LLM, no fabrication.

Each family lists candidate hypotheses. Generation only emits a hypothesis when
weighted evidence matches its support cues.
"""

from __future__ import annotations

from typing import Any

CATALOG_ID = "ihg-hypothesis-catalog-v1.0.0"
CATALOG_VERSION = "1.0.0"

# Families keyed by question-cue matchers (any substring hit activates family).
FAMILIES: list[dict[str, Any]] = [
    {
        "family_id": "margin_decline",
        "cues": ("margin", "margins", "gross margin", "ebitda margin", "operating margin"),
        "hypotheses": [
            {
                "key": "input_cost_inflation",
                "hypothesis": "Input-cost inflation compressed margins",
                "category": "Company",
                "framework": "FW_MARGIN_BRIDGE",
                "support_cues": ("cost", "input", "inflation", "commodity", "raw material", "cogs", "power", "wage"),
                "conflict_cues": ("pricing power", "cost deflation", "cost decline", "efficiency gain"),
            },
            {
                "key": "pricing_pressure",
                "hypothesis": "Pricing pressure reduced realized prices / mix",
                "category": "Industry",
                "framework": "FW_COMPETITIVE_INTENSITY",
                "support_cues": ("pricing", "price cut", "discount", "asp", "competitive", "pricing pressure"),
                "conflict_cues": ("price hike", "price increase", "premium pricing"),
            },
            {
                "key": "demand_weakness",
                "hypothesis": "Demand weakness reduced operating leverage",
                "category": "Macro",
                "framework": "FW_DEMAND_CYCLE",
                "support_cues": ("demand", "volume", "utilization", "orders", "weak demand", "slowdown"),
                "conflict_cues": ("volume growth", "strong demand", "order book"),
            },
            {
                "key": "execution_issues",
                "hypothesis": "Execution / operating issues weighed on margins",
                "category": "Company",
                "framework": "FW_OPERATING_QUALITY",
                "support_cues": ("execution", "delay", "disruption", "inefficiency", "one-off", "operational"),
                "conflict_cues": ("smooth execution", "on-time", "efficiency"),
            },
            {
                "key": "product_mix",
                "hypothesis": "Product-mix deterioration lowered blended margins",
                "category": "Company",
                "framework": "FW_MIX_ANALYSIS",
                "support_cues": ("mix", "product mix", "segment mix", "lower-margin", "mix shift"),
                "conflict_cues": ("favourable mix", "favorable mix", "premium mix"),
            },
        ],
    },
    {
        "family_id": "post_earnings_drawdown",
        "cues": ("stock fell", "shares fell", "selloff", "after earnings", "post earnings", "reacted", "dropped after"),
        "hypotheses": [
            {
                "key": "guidance_disappointment",
                "hypothesis": "Guidance disappointment drove the post-earnings move",
                "category": "Company",
                "framework": "FW_EXPECTATIONS",
                "support_cues": ("guidance", "outlook", "cut guidance", "lowered outlook", "miss"),
                "conflict_cues": ("raised guidance", "beat guidance", "strong outlook"),
            },
            {
                "key": "valuation_rich",
                "hypothesis": "Valuation was already expensive into the print",
                "category": "Valuation",
                "framework": "FW_HISTORICAL_VALUATION",
                "support_cues": ("valuation", "expensive", "premium", "multiple", "pe ", "p/e", "rich"),
                "conflict_cues": ("cheap", "discount", "undervalued"),
            },
            {
                "key": "weak_cash_flow",
                "hypothesis": "Weak cash-flow quality undermined the earnings beat/miss narrative",
                "category": "Accounting",
                "framework": "FW_CASH_CONVERSION",
                "support_cues": ("cash flow", "fcf", "working capital", "receivable", "cash conversion"),
                "conflict_cues": ("strong fcf", "cash generation", "cash conversion improved"),
            },
            {
                "key": "margin_concern",
                "hypothesis": "Margin concern dominated the market reaction",
                "category": "Company",
                "framework": "FW_MARGIN_BRIDGE",
                "support_cues": ("margin", "profitability", "gross margin", "ebitda"),
                "conflict_cues": ("margin expansion", "margin beat"),
            },
            {
                "key": "management_commentary",
                "hypothesis": "Management commentary shifted the narrative negatively",
                "category": "Governance",
                "framework": "FW_MANAGEMENT_QUALITY",
                "support_cues": ("management", "commentary", "conference call", "tone", "cautious"),
                "conflict_cues": ("confident tone", "constructive commentary"),
            },
        ],
    },
    {
        "family_id": "valuation_premium",
        "cues": ("trading at a premium", "premium valuation", "why premium", "trades at a premium", "why is", "premium to"),
        "hypotheses": [
            {
                "key": "higher_roe",
                "hypothesis": "Higher ROE sustains a valuation premium",
                "category": "Valuation",
                "framework": "FW_PB",
                "support_cues": ("roe", "return on equity", "profitability", "returns"),
                "conflict_cues": ("roe compression", "low roe"),
            },
            {
                "key": "asset_quality",
                "hypothesis": "Superior asset quality justifies the premium",
                "category": "Risk",
                "framework": "FW_CREDIT_QUALITY",
                "support_cues": ("asset quality", "npa", "nnpa", "credit cost", "slippages", "gnpas"),
                "conflict_cues": ("asset quality stress", "npa spike"),
            },
            {
                "key": "deposit_franchise",
                "hypothesis": "Deposit franchise / liability advantage supports the premium",
                "category": "Company",
                "framework": "FW_BANK_FRANCHISE",
                "support_cues": ("deposit", "casa", "franchise", "liability", "funding"),
                "conflict_cues": ("deposit pressure", "funding cost spike"),
            },
            {
                "key": "long_term_growth",
                "hypothesis": "Long-term growth optionality underpins the premium",
                "category": "Company",
                "framework": "FW_GROWTH_DURATION",
                "support_cues": ("growth", "loan growth", "expansion", "market share"),
                "conflict_cues": ("growth slowdown", "deceleration"),
            },
            {
                "key": "valuation_expansion",
                "hypothesis": "Multiple expansion (not fundamentals alone) explains the premium",
                "category": "Valuation",
                "framework": "FW_EXPECTATIONS",
                "support_cues": ("multiple expansion", "re-rating", "sentiment", "flows", "premium expanded"),
                "conflict_cues": ("de-rating", "multiple compression"),
            },
        ],
    },
    {
        "family_id": "earnings_quality",
        "cues": ("earnings quality", "accounting", "accrual", "cash conversion", "why profit"),
        "hypotheses": [
            {
                "key": "accrual_driven",
                "hypothesis": "Accrual / working-capital effects inflated reported earnings",
                "category": "Accounting",
                "framework": "FW_EARNINGS_QUALITY",
                "support_cues": ("accrual", "receivable", "inventory", "working capital", "deferred"),
                "conflict_cues": ("cash earnings", "high cash conversion"),
            },
            {
                "key": "one_off_gain",
                "hypothesis": "One-off gains contributed materially to reported profit",
                "category": "Accounting",
                "framework": "FW_EARNINGS_QUALITY",
                "support_cues": ("one-off", "one off", "exceptional", "other income", "non-recurring"),
                "conflict_cues": ("core earnings", "recurring"),
            },
            {
                "key": "core_operating",
                "hypothesis": "Core operating improvement explains the earnings change",
                "category": "Company",
                "framework": "FW_OPERATING_QUALITY",
                "support_cues": ("operating profit", "ebit", "core", "volume", "realization"),
                "conflict_cues": ("operating decline",),
            },
        ],
    },
    {
        "family_id": "capital_allocation",
        "cues": ("buyback", "dividend", "capex", "capital allocation", "m&a", "acquisition", "buy-back"),
        "hypotheses": [
            {
                "key": "shareholder_return_focus",
                "hypothesis": "Management prioritised shareholder returns over reinvestment",
                "category": "CapitalAllocation",
                "framework": "FW_CAPITAL_ALLOCATION",
                "support_cues": ("buyback", "dividend", "payout", "shareholder return"),
                "conflict_cues": ("reinvestment", "growth capex"),
            },
            {
                "key": "growth_reinvestment",
                "hypothesis": "Capital is being reinvested for growth",
                "category": "CapitalAllocation",
                "framework": "FW_CAPITAL_ALLOCATION",
                "support_cues": ("capex", "expansion", "capacity", "investment"),
                "conflict_cues": ("capex cut", "deferred investment"),
            },
            {
                "key": "mna_driven",
                "hypothesis": "M&A / inorganic moves are shaping capital deployment",
                "category": "CapitalAllocation",
                "framework": "FW_CAPITAL_ALLOCATION",
                "support_cues": ("acquisition", "m&a", "merger", "deal"),
                "conflict_cues": ("no acquisition", "organic only"),
            },
        ],
    },
    {
        "family_id": "generic_why",
        "cues": ("why", "what explains", "what drove", "driver", "reason"),
        "hypotheses": [
            {
                "key": "company_specific",
                "hypothesis": "Company-specific fundamentals are the primary driver",
                "category": "Company",
                "framework": "FW_FUNDAMENTAL_DRIVER",
                "support_cues": ("company", "management", "segment", "product", "execution", "margin", "revenue"),
                "conflict_cues": ("sector-wide", "macro-driven"),
            },
            {
                "key": "industry_cycle",
                "hypothesis": "Industry / competitive cycle effects dominate",
                "category": "Industry",
                "framework": "FW_INDUSTRY_STRUCTURE",
                "support_cues": ("industry", "sector", "competitive", "peers", "cycle"),
                "conflict_cues": ("idiosyncratic", "company-only"),
            },
            {
                "key": "macro_policy",
                "hypothesis": "Macro / policy conditions are a material explanation",
                "category": "Macro",
                "framework": "FW_MACRO_REGIME",
                "support_cues": ("macro", "rates", "inflation", "policy", "gdp", "liquidity", "rupee"),
                "conflict_cues": ("company-specific only",),
            },
            {
                "key": "valuation_sentiment",
                "hypothesis": "Valuation / sentiment dynamics explain the outcome more than fundamentals",
                "category": "Valuation",
                "framework": "FW_EXPECTATIONS",
                "support_cues": ("valuation", "multiple", "sentiment", "flows", "premium", "discount"),
                "conflict_cues": ("fundamental re-rating justified",),
            },
        ],
    },
]

CATALOG: dict[str, Any] = {
    "catalog_id": CATALOG_ID,
    "version": CATALOG_VERSION,
    "families": FAMILIES,
    "deterministic": True,
    "llm_used": False,
}
