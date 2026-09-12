"""IIEX v1.0 question bank — CIO Investment Committee Assessment (31 questions)."""

from __future__ import annotations

from typing import Any

# Marks sum to 600 as specified in the committee brief.
# Normalized score maps to /500 with pass at 450 (90%).

QUESTIONS: list[dict[str, Any]] = [
    # ---- Section A — Company Intelligence (100) ----
    {
        "id": "Q1",
        "section": "A_Company",
        "marks": 30,
        "title": "Full Company Initiation Report — Reliance Industries",
        "prompt": (
            "Prepare a complete institutional initiation report on Reliance Industries Ltd. "
            "Include Executive Summary, Business Overview, Segment Analysis, Revenue Drivers, "
            "Competitive Advantages, Management Assessment, Industry Position, Financial Analysis, "
            "Historical Performance, Risks, Valuation, Bull/Base/Bear Scenarios, Investment Conclusion, "
            "Confidence Score and Supporting Evidence."
        ),
        "entity": "RELIANCE",
        "required_sections": [
            "executive_summary",
            "business_overview",
            "segment_analysis",
            "revenue_drivers",
            "competitive_advantages",
            "management_assessment",
            "industry_position",
            "financial_analysis",
            "historical_performance",
            "risks",
            "valuation",
            "scenarios",
            "investment_conclusion",
            "confidence",
            "supporting_evidence",
        ],
        "platforms": ["company", "ifi", "sfi", "mkfi", "rih"],
        "dimensions": ["accuracy", "reasoning", "evidence", "forecasting", "communication"],
    },
    {
        "id": "Q2",
        "section": "A_Company",
        "marks": 20,
        "title": "Earnings Intelligence — Infosys",
        "prompt": (
            "Infosys reports Revenue +9%, EBIT Margin -120 bps, Raised FY Guidance, "
            "Attrition falls, Deal Wins at record high. Analyse why margins declined, "
            "whether guidance is more important, impact on valuation, sector implications, "
            "historical comparison and forecast revision."
        ),
        "entity": "INFY",
        "required_sections": [
            "margin_diagnosis",
            "guidance_vs_margins",
            "valuation_impact",
            "sector_implications",
            "historical_comparison",
            "forecast_revision",
            "supporting_evidence",
        ],
        "platforms": ["company", "sfi", "hmkai", "ifi"],
        "dimensions": ["accuracy", "reasoning", "historical_context", "evidence"],
    },
    {
        "id": "Q3",
        "section": "A_Company",
        "marks": 20,
        "title": "Company Comparison — HDFC Bank vs ICICI Bank",
        "prompt": (
            "Compare HDFC Bank and ICICI Bank on business quality, loan growth, CASA, "
            "asset quality, capital adequacy, ROE, valuation and long-term investment attractiveness."
        ),
        "entity": "HDFCBANK,ICICIBANK",
        "required_sections": [
            "business_quality",
            "loan_growth",
            "casa",
            "asset_quality",
            "capital_adequacy",
            "roe",
            "valuation",
            "long_term_attractiveness",
            "supporting_evidence",
        ],
        "platforms": ["company", "sfi", "ifi"],
        "dimensions": ["accuracy", "reasoning", "evidence", "communication"],
    },
    {
        "id": "Q4",
        "section": "A_Company",
        "marks": 15,
        "title": "Event Analysis — ₹25,000 crore Acquisition",
        "prompt": (
            "A company announces a ₹25,000 crore acquisition. Analyse strategic rationale, "
            "synergies, financial impact, integration risks and historical analogues."
        ),
        "entity": "RELIANCE",
        "required_sections": [
            "strategic_rationale",
            "synergies",
            "financial_impact",
            "integration_risks",
            "historical_analogues",
            "supporting_evidence",
        ],
        "platforms": ["company", "hmkai", "mkri", "ifi"],
        "dimensions": ["reasoning", "historical_context", "relationships", "evidence"],
    },
    {
        "id": "Q5",
        "section": "A_Company",
        "marks": 15,
        "title": "Risk Assessment — Tata Motors Top 10",
        "prompt": (
            "Identify the top 10 risks for Tata Motors over the next two years. "
            "Rank them by probability and impact."
        ),
        "entity": "TATAMOTORS",
        "required_sections": [
            "risk_register",
            "probability_impact_matrix",
            "ranking",
            "supporting_evidence",
        ],
        "platforms": ["company", "sfi", "mfi", "mkfi"],
        "dimensions": ["accuracy", "reasoning", "evidence"],
    },
    # ---- Section B — Market Intelligence (75) ----
    {
        "id": "Q6",
        "section": "B_Market",
        "marks": 20,
        "title": "Market Open Analysis — Pre-Market 08:30",
        "prompt": (
            "Generate a complete pre-market report at 8:30 AM. Assume Dow +1.4%, Nasdaq +2%, "
            "Brent +4%, Gold flat, USDINR 84.1, Gift Nifty +120. Produce Executive Summary, "
            "Market Outlook, Sectors to Watch, Stocks to Watch, Risks and Trading Themes."
        ),
        "entity": "India",
        "required_sections": [
            "executive_summary",
            "market_outlook",
            "sectors_to_watch",
            "stocks_to_watch",
            "risks",
            "trading_themes",
            "supporting_evidence",
        ],
        "platforms": ["cmktp", "mkfi", "sfi", "mkri"],
        "dimensions": ["reasoning", "forecasting", "communication", "evidence"],
        "assumptions": {
            "dow": "+1.4%",
            "nasdaq": "+2%",
            "brent": "+4%",
            "gold": "flat",
            "usdinr": 84.1,
            "gift_nifty": "+120",
        },
    },
    {
        "id": "Q7",
        "section": "B_Market",
        "marks": 15,
        "title": "Institutional Flow Analysis",
        "prompt": (
            "FIIs sold ₹8,000 crore. DIIs bought ₹7,600 crore. NIFTY closed +0.3%. "
            "Explain market interpretation, breadth, liquidity, positioning and historical comparison."
        ),
        "entity": "India",
        "required_sections": [
            "interpretation",
            "breadth",
            "liquidity",
            "positioning",
            "historical_comparison",
            "supporting_evidence",
        ],
        "platforms": ["cmktp", "hmkip", "hmkai", "mkri"],
        "dimensions": ["reasoning", "historical_context", "evidence"],
        "assumptions": {"fii": -8000, "dii": 7600, "nifty": "+0.3%"},
    },
    {
        "id": "Q8",
        "section": "B_Market",
        "marks": 20,
        "title": "Market Health Assessment",
        "prompt": (
            "Determine Market Regime, Breadth, Liquidity, Leadership, Volatility and "
            "Market Health Score. Explain every conclusion."
        ),
        "entity": "India",
        "required_sections": [
            "market_regime",
            "breadth",
            "liquidity",
            "leadership",
            "volatility",
            "health_score",
            "explanations",
            "supporting_evidence",
        ],
        "platforms": ["cmktp", "mkfi", "hmkai"],
        "dimensions": ["accuracy", "reasoning", "evidence"],
    },
    {
        "id": "Q9",
        "section": "B_Market",
        "marks": 20,
        "title": "Correction Analysis — NIFTY -10%",
        "prompt": (
            "NIFTY falls 10%. Determine whether it is a healthy correction, bear market, "
            "panic or opportunity. Support your reasoning."
        ),
        "entity": "India",
        "required_sections": [
            "classification",
            "reasoning",
            "historical_analogues",
            "opportunity_assessment",
            "supporting_evidence",
        ],
        "platforms": ["hmkai", "mkfi", "cmktp", "hmkip"],
        "dimensions": ["reasoning", "historical_context", "forecasting", "evidence"],
    },
    # ---- Section C — Macro Intelligence (75) ----
    {
        "id": "Q10",
        "section": "C_Macro",
        "marks": 25,
        "title": "RBI Policy Analysis — 50 bps Cut",
        "prompt": (
            "RBI cuts Repo by 50 bps. Inflation remains at 6.3%. Analyse Banking, NBFC, Realty, "
            "Auto, Currency, Bonds, GDP and Risks."
        ),
        "entity": "India",
        "required_sections": [
            "banking",
            "nbfc",
            "realty",
            "auto",
            "currency",
            "bonds",
            "gdp",
            "risks",
            "supporting_evidence",
        ],
        "platforms": ["mfi", "mkri", "sfi", "hmkai"],
        "dimensions": ["reasoning", "relationships", "forecasting", "evidence"],
        "assumptions": {"repo_cut_bps": 50, "inflation": 6.3},
    },
    {
        "id": "Q11",
        "section": "C_Macro",
        "marks": 20,
        "title": "Inflation Shock — Oil +25%",
        "prompt": (
            "Oil rises 25%. Analyse impact on Inflation, Monetary policy, Corporate margins, "
            "Market valuation and Consumers."
        ),
        "entity": "India",
        "required_sections": [
            "inflation",
            "monetary_policy",
            "corporate_margins",
            "market_valuation",
            "consumers",
            "supporting_evidence",
        ],
        "platforms": ["mfi", "mkri", "mkfi", "sfi"],
        "dimensions": ["reasoning", "relationships", "evidence"],
        "assumptions": {"oil_shock_pct": 25},
    },
    {
        "id": "Q12",
        "section": "C_Macro",
        "marks": 15,
        "title": "Budget Analysis — Infra Package",
        "prompt": (
            "Government announces ₹2 lakh crore infrastructure package; corporate tax unchanged. "
            "Determine beneficiaries."
        ),
        "entity": "India",
        "required_sections": [
            "beneficiaries",
            "sector_impact",
            "company_impact",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "mkri", "mfi"],
        "dimensions": ["reasoning", "relationships", "evidence"],
    },
    {
        "id": "Q13",
        "section": "C_Macro",
        "marks": 15,
        "title": "Global Macro — US Recession",
        "prompt": "US enters recession. Explain implications for India.",
        "entity": "Global",
        "required_sections": [
            "transmission_channels",
            "india_implications",
            "sector_winners_losers",
            "supporting_evidence",
        ],
        "platforms": ["mfi", "mkfi", "mkri", "hmkai"],
        "dimensions": ["reasoning", "relationships", "historical_context", "evidence"],
    },
    # ---- Section D — Sector Intelligence (75) ----
    {
        "id": "Q14",
        "section": "D_Sector",
        "marks": 20,
        "title": "Banking Sector — Six-Month Outlook",
        "prompt": (
            "Prepare a six-month banking sector outlook including Growth, Risks, Valuation, "
            "Forecast and Catalysts."
        ),
        "entity": "Banking",
        "required_sections": [
            "growth",
            "risks",
            "valuation",
            "forecast",
            "catalysts",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "mfi", "mkfi", "hsai"],
        "dimensions": ["forecasting", "reasoning", "evidence"],
    },
    {
        "id": "Q15",
        "section": "D_Sector",
        "marks": 15,
        "title": "IT Sector — USD +8%",
        "prompt": "USD strengthens 8%. Analyse impact on IT Services.",
        "entity": "IT Services",
        "required_sections": [
            "revenue_impact",
            "margin_impact",
            "valuation_impact",
            "company_implications",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "mkri", "mfi"],
        "dimensions": ["relationships", "reasoning", "evidence"],
        "assumptions": {"usd_strength_pct": 8},
    },
    {
        "id": "Q16",
        "section": "D_Sector",
        "marks": 15,
        "title": "Defence Sector — Spend +20%",
        "prompt": "Government increases defence spending by 20%. Determine beneficiaries.",
        "entity": "Defence",
        "required_sections": [
            "beneficiaries",
            "order_book_implications",
            "risks",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "mkri", "cskp"],
        "dimensions": ["reasoning", "relationships", "evidence"],
        "assumptions": {"defence_spend_pct": 20},
    },
    {
        "id": "Q17",
        "section": "D_Sector",
        "marks": 10,
        "title": "Auto Sector — EV Adoption Doubles",
        "prompt": "EV adoption doubles. Analyse winners and losers.",
        "entity": "Auto",
        "required_sections": [
            "winners",
            "losers",
            "transition_risks",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "cskp", "mkri"],
        "dimensions": ["reasoning", "evidence"],
    },
    {
        "id": "Q18",
        "section": "D_Sector",
        "marks": 15,
        "title": "Capital Goods — Capex Surge",
        "prompt": "Government capex increases significantly. Explain implications.",
        "entity": "Capital Goods",
        "required_sections": [
            "demand_implications",
            "company_beneficiaries",
            "risks",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "mfi", "mkri"],
        "dimensions": ["reasoning", "relationships", "evidence"],
    },
    # ---- Section E — IPO Intelligence (40) ----
    {
        "id": "Q19",
        "section": "E_IPO",
        "marks": 20,
        "title": "IPO Analysis — Manufacturing at 48x",
        "prompt": (
            "A manufacturing IPO launches at 48x earnings. Prepare an IPO research note covering "
            "Business, Financials, Valuation, Peer Comparison, Risks, Listing Outlook and Long-term Outlook."
        ),
        "entity": "IPO_MANUFACTURING",
        "required_sections": [
            "business",
            "financials",
            "valuation",
            "peer_comparison",
            "risks",
            "listing_outlook",
            "long_term_outlook",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "ifi", "mkfi", "rih"],
        "dimensions": ["reasoning", "evidence", "research_quality", "communication"],
        "assumptions": {"ipo_pe": 48, "sector": "Capital Goods"},
    },
    {
        "id": "Q20",
        "section": "E_IPO",
        "marks": 20,
        "title": "IPO Comparison — Two Recent Listings",
        "prompt": (
            "Compare two recently listed IPOs and determine which is the better investment."
        ),
        "entity": "IPO_COMPARE",
        "required_sections": [
            "ipo_a",
            "ipo_b",
            "comparison_matrix",
            "recommendation",
            "supporting_evidence",
        ],
        "platforms": ["sfi", "ifi", "rih"],
        "dimensions": ["reasoning", "research_quality", "evidence", "portfolio_thinking"],
    },
    # ---- Section F — Relationship Intelligence (40) ----
    {
        "id": "Q21",
        "section": "F_Relationship",
        "marks": 20,
        "title": "Relationship Mapping",
        "prompt": (
            "Map relationships for Oil, USD, Inflation, RBI, Banks, Auto, IT and Airlines. "
            "Create an explainable relationship chain."
        ),
        "entity": "India",
        "required_sections": [
            "relationship_map",
            "relationship_chain",
            "direction_strength_confidence",
            "supporting_evidence",
        ],
        "platforms": ["mkri", "mri", "sri"],
        "dimensions": ["relationships", "reasoning", "evidence"],
    },
    {
        "id": "Q22",
        "section": "F_Relationship",
        "marks": 20,
        "title": "Causal Analysis — Fed +75 bps",
        "prompt": (
            "Fed hikes 75 bps. Explain every downstream impact on Indian markets."
        ),
        "entity": "Global",
        "required_sections": [
            "transmission_chain",
            "currency",
            "flows",
            "rates",
            "equities",
            "sectors",
            "supporting_evidence",
        ],
        "platforms": ["mkri", "mfi", "mkfi", "hmkai"],
        "dimensions": ["relationships", "reasoning", "historical_context", "evidence"],
        "assumptions": {"fed_hike_bps": 75},
    },
    # ---- Section G — Historical Intelligence (30) ----
    {
        "id": "Q23",
        "section": "G_Historical",
        "marks": 15,
        "title": "Historical Context — Inflation vs 2022",
        "prompt": "Current inflation resembles 2022. Compare both periods.",
        "entity": "India",
        "required_sections": [
            "similarities",
            "differences",
            "policy_response",
            "market_outcomes",
            "supporting_evidence",
        ],
        "platforms": ["hmkai", "hmkip", "hmai", "mfi"],
        "dimensions": ["historical_context", "reasoning", "evidence"],
    },
    {
        "id": "Q24",
        "section": "G_Historical",
        "marks": 15,
        "title": "Historical Analogues — Top 3 Environments",
        "prompt": (
            "Find the three most similar historical market environments and explain why."
        ),
        "entity": "India",
        "required_sections": [
            "analogue_1",
            "analogue_2",
            "analogue_3",
            "similarity_rationale",
            "supporting_evidence",
        ],
        "platforms": ["hmkai", "cmktp", "hmkip"],
        "dimensions": ["historical_context", "accuracy", "evidence"],
    },
    # ---- Section H — Forecast Intelligence (40) ----
    {
        "id": "Q25",
        "section": "H_Forecast",
        "marks": 20,
        "title": "Market Forecast — Next Six Months",
        "prompt": (
            "Forecast the next six months. Produce Bull, Base, Bear, Probability, Confidence, "
            "Risks and Catalysts."
        ),
        "entity": "India",
        "required_sections": [
            "bull",
            "base",
            "bear",
            "probability",
            "confidence",
            "risks",
            "catalysts",
            "supporting_evidence",
        ],
        "platforms": ["mkfi", "mfi", "hmkai", "cmktp"],
        "dimensions": ["forecasting", "reasoning", "evidence"],
    },
    {
        "id": "Q26",
        "section": "H_Forecast",
        "marks": 20,
        "title": "Company Forecast — Reliance 12 Months",
        "prompt": "Forecast Reliance Industries for the next 12 months.",
        "entity": "RELIANCE",
        "required_sections": [
            "scenarios",
            "probability",
            "confidence",
            "catalysts",
            "risks",
            "supporting_evidence",
        ],
        "platforms": ["ifi", "mkfi", "sfi", "company"],
        "dimensions": ["forecasting", "accuracy", "evidence"],
    },
    # ---- Section I — Research Intelligence (60) ----
    {
        "id": "Q27",
        "section": "I_Research",
        "marks": 30,
        "title": "Research Synthesis — Multi-Source Note",
        "prompt": (
            "Given one broker report, one company filing, one macro release and one market news "
            "article, produce one institutional research note with Executive Summary, Why It Matters, "
            "Company Impact, Sector Impact, Market Impact, Historical Context, Forecast and "
            "Supporting Evidence."
        ),
        "entity": "RELIANCE",
        "required_sections": [
            "executive_summary",
            "why_it_matters",
            "company_impact",
            "sector_impact",
            "market_impact",
            "historical_context",
            "forecast",
            "supporting_evidence",
        ],
        "platforms": ["rih", "ifi", "mkfi", "sfi", "mfi", "hmkai"],
        "dimensions": ["research_quality", "communication", "evidence", "forecasting"],
    },
    {
        "id": "Q28",
        "section": "I_Research",
        "marks": 15,
        "title": "Research Prioritisation",
        "prompt": (
            "Rank ten research notes by importance for an institutional portfolio manager. "
            "Explain the ranking."
        ),
        "entity": "India",
        "required_sections": [
            "ranked_notes",
            "ranking_rationale",
            "supporting_evidence",
        ],
        "platforms": ["rih"],
        "dimensions": ["portfolio_thinking", "research_quality", "reasoning"],
    },
    {
        "id": "Q29",
        "section": "I_Research",
        "marks": 15,
        "title": "Contradictory Research",
        "prompt": (
            "Two brokers have opposite recommendations. Produce AGIB's independent conclusion "
            "and explain why."
        ),
        "entity": "INFY",
        "required_sections": [
            "broker_a_view",
            "broker_b_view",
            "agi_independent_conclusion",
            "evidence_weighing",
            "supporting_evidence",
        ],
        "platforms": ["ifi", "sfi", "rih", "company"],
        "dimensions": ["research_quality", "reasoning", "evidence"],
    },
    # ---- Section J — CIO Investment Committee (65) ----
    {
        "id": "Q30",
        "section": "J_CIO_Committee",
        "marks": 35,
        "title": "Morning Investment Committee Brief — 08:15 IST",
        "prompt": (
            "Time: 8:15 AM IST. Assume US markets mixed, Brent +5%, Gold +1%, RBI policy today, "
            "Infosys beats earnings, Defence IPO opens, FIIs sold ₹4,000 crore, Gift Nifty +80. "
            "Prepare a morning note for institutional clients."
        ),
        "entity": "India",
        "required_sections": [
            "executive_summary",
            "overnight_tape",
            "policy_watch",
            "earnings",
            "ipo_watch",
            "flows",
            "market_plan",
            "risks",
            "supporting_evidence",
        ],
        "platforms": ["rih", "mkfi", "mfi", "sfi", "cmktp", "ifi"],
        "dimensions": ["communication", "portfolio_thinking", "reasoning", "evidence", "forecasting"],
        "assumptions": {
            "brent": "+5%",
            "gold": "+1%",
            "rbi_policy_today": True,
            "infosys_beats": True,
            "defence_ipo": True,
            "fii": -4000,
            "gift_nifty": "+80",
        },
    },
    {
        "id": "Q31",
        "section": "J_CIO_Committee",
        "marks": 30,
        "title": "Portfolio Strategy — ₹500 crore India Equity Fund",
        "prompt": (
            "You manage a ₹500 crore India equity fund. Environment: Inflation easing, RBI expected "
            "to cut rates, FII inflows increasing, IT expensive, Banks undervalued. Recommend "
            "Asset allocation, Sector allocation, Top 10 ideas, Risks, Cash level, Hedging strategy "
            "and Monitoring triggers."
        ),
        "entity": "India",
        "required_sections": [
            "asset_allocation",
            "sector_allocation",
            "top_10_ideas",
            "risks",
            "cash_level",
            "hedging_strategy",
            "monitoring_triggers",
            "supporting_evidence",
        ],
        "platforms": ["mkfi", "sfi", "mfi", "ifi", "cmktp"],
        "dimensions": ["portfolio_thinking", "forecasting", "reasoning", "evidence", "communication"],
        "assumptions": {
            "aum_crore": 500,
            "inflation": "easing",
            "rbi": "cut_expected",
            "fii": "inflows",
            "it": "expensive",
            "banks": "undervalued",
        },
    },
]


def all_questions() -> list[dict[str, Any]]:
    return list(QUESTIONS)


def question_by_id(qid: str) -> dict[str, Any] | None:
    for q in QUESTIONS:
        if q["id"] == qid:
            return dict(q)
    return None


def total_marks() -> int:
    return sum(int(q["marks"]) for q in QUESTIONS)


def section_totals() -> dict[str, int]:
    out: dict[str, int] = {}
    for q in QUESTIONS:
        out[q["section"]] = out.get(q["section"], 0) + int(q["marks"])
    return out
