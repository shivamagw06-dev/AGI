"""Ask Intelligence Constitution v1.0 — institutional response methodology (code, not prompt)."""

from __future__ import annotations

CONSTITUTION_VERSION = "1.0"
PROGRAMME = "AGI Ask Intelligence Constitution — Institutional Response Methodology"
SCOPE = "Every Ask query inside AGI Investment OS"

# Primary investment intents (constitution taxonomy)
PRIMARY_INTENTS: tuple[str, ...] = (
    "INVESTMENT_ASSESSMENT",
    "VALUATION",
    "BUSINESS_QUALITY",
    "FINANCIAL_ANALYSIS",
    "EARNINGS_ANALYSIS",
    "RISK_ANALYSIS",
    "MANAGEMENT_ANALYSIS",
    "COMPETITIVE_POSITION",
    "SECTOR_ANALYSIS",
    "MACRO_ANALYSIS",
    "PORTFOLIO_ANALYSIS",
    "PEER_COMPARISON",
    "THESIS_CHANGE",
    "NEWS_IMPACT",
    "MARKET_OVERVIEW",
    "PORTFOLIO_MONITORING",
    "WATCHLIST",
    "EDUCATION",
)

# Map IRL v2 intent → constitution primary intent
IRL_TO_CONSTITUTION: dict[str, str] = {
    "Analyse": "INVESTMENT_ASSESSMENT",
    "Valuation": "VALUATION",
    "Compare": "PEER_COMPARISON",
    "Portfolio": "PORTFOLIO_ANALYSIS",
    "Risk": "RISK_ANALYSIS",
    "Explain": "EDUCATION",
    "Education": "EDUCATION",
    "Industry": "SECTOR_ANALYSIS",
    "Macro": "MACRO_ANALYSIS",
    "Government": "MACRO_ANALYSIS",
    "CorporateEvents": "NEWS_IMPACT",
    "Documents": "FINANCIAL_ANALYSIS",
    "Accounting": "FINANCIAL_ANALYSIS",
    "HistoricalReplay": "THESIS_CHANGE",
    "CrossDomain": "INVESTMENT_ASSESSMENT",
    "Unknown": "EDUCATION",
}

# Real intent patterns (question text → investment intent clarification)
REAL_INTENT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"\bshould i buy\b|\bbuy\b.*\?", "INVESTMENT_ASSESSMENT", "Determine whether the company deserves investment consideration"),
    (r"\bexpensive\b|\bcheap\b|\bovervalued\b|\bundervalued\b", "VALUATION", "Evaluate current valuation versus history and expectations"),
    (r"\bearnings\b|\bresults\b|\bquarter", "EARNINGS_ANALYSIS", "Determine whether earnings changed the investment thesis"),
    (r"\bmoat\b|\bcompetitive\b|\bbusiness quality\b", "BUSINESS_QUALITY", "Assess sustainable competitive advantage"),
    (r"\bportfolio\b|\bholdings\b|\ballocation\b", "PORTFOLIO_ANALYSIS", "Evaluate fit within portfolio context"),
    (r"\bwhat changed\b|\bthesis\b", "THESIS_CHANGE", "Identify what changed in the investment thesis"),
    (r"\bnews\b|\bannounced\b|\bheadline\b", "NEWS_IMPACT", "Assess investment significance of the development"),
    (r"\bmarket\b|\bnifty\b|\bsensex\b", "MARKET_OVERVIEW", "Understand current market state and research focus"),
)

# Approved methodology steps per constitution intent
METHODOLOGY: dict[str, tuple[str, ...]] = {
    "INVESTMENT_ASSESSMENT": (
        "Business Quality",
        "Financial Strength",
        "Management",
        "Growth",
        "Valuation",
        "Risks",
        "Portfolio Context",
        "Research Conclusion",
    ),
    "VALUATION": ("Current Level", "Historical Context", "Peer Context", "Growth/ROE Context", "Implications"),
    "EARNINGS_ANALYSIS": ("What Changed", "Why", "Temporary vs Structural", "Thesis Impact", "Research Conclusion"),
    "PEER_COMPARISON": ("Peer Set", "Metric Comparison", "Quality Differences", "Valuation Differences", "Research Conclusion"),
    "PORTFOLIO_ANALYSIS": ("Holdings Context", "Concentration", "Correlation", "Opportunity Cost", "Research Conclusion"),
    "RISK_ANALYSIS": ("Business Risk", "Financial Risk", "Industry Risk", "Macro Risk", "Monitoring Indicators"),
    "EDUCATION": ("Concept", "Mechanism", "Investment Relevance", "Examples"),
    "MACRO_ANALYSIS": ("Macro Driver", "Transmission", "Sector Impact", "Monitoring"),
    "SECTOR_ANALYSIS": ("Sector Dynamics", "Valuation", "Key Drivers", "Risks", "Research Conclusion"),
    "NEWS_IMPACT": ("Event", "Revenue Impact", "Margin Impact", "Thesis Impact", "No Meaningful Impact"),
    "THESIS_CHANGE": ("Prior View", "What Changed", "Evidence Delta", "Updated Questions"),
    "MARKET_OVERVIEW": ("Regime", "Valuation", "Breadth", "Flows", "Research Priorities"),
}

# Required intelligence engines per constitution intent
REQUIRED_INTELLIGENCE: dict[str, tuple[str, ...]] = {
    "INVESTMENT_ASSESSMENT": (
        "Company Intelligence",
        "Financial Intelligence",
        "Valuation Intelligence",
        "Evidence Intelligence",
        "Sector Intelligence",
        "Risk Intelligence",
    ),
    "VALUATION": ("Valuation Intelligence", "Financial Intelligence", "Historical Intelligence"),
    "EARNINGS_ANALYSIS": ("Financial Intelligence", "Forecast Intelligence", "Evidence Intelligence"),
    "PEER_COMPARISON": ("Company Intelligence", "Valuation Intelligence", "Financial Intelligence"),
    "PORTFOLIO_ANALYSIS": ("Portfolio Intelligence", "Valuation Intelligence", "Risk Intelligence"),
    "RISK_ANALYSIS": ("Risk Intelligence", "Financial Intelligence", "Governance Intelligence"),
    "MACRO_ANALYSIS": ("Macro Intelligence", "Sector Intelligence", "Market Intelligence"),
    "SECTOR_ANALYSIS": ("Sector Intelligence", "Valuation Intelligence", "Macro Intelligence"),
    "EDUCATION": ("Evidence Intelligence",),
    "NEWS_IMPACT": ("Evidence Intelligence", "Company Intelligence", "Forecast Intelligence"),
    "THESIS_CHANGE": ("Historical Intelligence", "Evidence Intelligence", "Company Intelligence"),
    "MARKET_OVERVIEW": ("Market Intelligence", "Macro Intelligence", "Sector Intelligence"),
}

# Constitution v1.0 output sections (investment assessment)
OUTPUT_SECTIONS: tuple[str, ...] = (
    "executive_summary",
    "investment_context",
    "business_quality",
    "financial_strength",
    "management",
    "growth_outlook",
    "valuation",
    "risks",
    "catalysts",
    "what_changed",
    "research_conclusion",
    "questions_before_you_decide",
    "supporting_intelligence",
    "evidence",
    "confidence",
)

FORBIDDEN_OUTPUTS: tuple[str, ...] = (
    "buy this stock",
    "sell this stock",
    "guaranteed returns",
    "target price",
    "entry price",
    "exit price",
    "multi-bagger",
    "strong buy",
    "must buy",
    "must sell",
    "will outperform",
    "definitely",
    "certainly",
    "guaranteed",
)

ALLOWED_PHRASES: tuple[str, ...] = (
    "research indicates",
    "evidence suggests",
    "current valuation appears",
    "historical evidence shows",
    "financial quality remains",
    "business quality appears",
    "current evidence supports",
    "current evidence does not support",
)

CONFIDENCE_METHODOLOGY = (
    "Confidence measures evidence reliability — not expected return. "
    "Components: evidence completeness, financial statement coverage, "
    "historical consistency, peer benchmark availability, and data quality (DQIV). "
    "Confidence must explain why it has that value."
)

INSTITUTIONAL_THINKING_QUESTIONS: tuple[str, ...] = (
    "What is the user really trying to decide?",
    "What evidence is required?",
    "Which intelligence engines are required?",
    "Which uncertainties remain?",
    "What assumptions are embedded in the current market price?",
    "What would make the investment thesis stronger?",
    "What would invalidate today's thesis?",
    "What questions should the investor answer before acting?",
)

VALIDATION_RULES: tuple[str, ...] = (
    "Intent classified before synthesis",
    "Methodology matches intent — never improvised",
    "Required intelligence collected or gaps stated",
    "Every conclusion traceable to evidence",
    "No BUY/SELL/TARGET/ENTRY/EXIT language",
    "Research conclusion — not investment instruction",
    "Confidence explains methodology",
    "Final decision belongs to the user",
)
