"""RQ1 Research Ontology — locked Sprint 1 constitution schema."""

from __future__ import annotations

from typing import Any

RQ1_VERSION = "1.0.0-sprint1"
PROGRAMME = "RQ1 Research Ontology"
PROGRAMME_SHORT = "RQ1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
SPRINT = 1
SPRINT_NAME = "Research Ontology"
NO_LAYER_EXECUTION = True
NO_ANALYST_EXECUTION = True

PRIMARY_INTENTS: dict[str, dict[str, str]] = {
    "company_research": {
        "label": "Company Research",
        "objective": "Investment Evaluation",
        "description": "Single-company analysis, buy/hold judgement framing, explain company.",
    },
    "sector_research": {
        "label": "Sector Research",
        "objective": "Relative Attractiveness",
        "description": "Sector attractiveness, sector beneficiaries, industry structure.",
    },
    "index_research": {
        "label": "Index Research",
        "objective": "Historical Valuation",
        "description": "Index valuation, index vs peers/history, market-level structure.",
    },
    "macro_research": {
        "label": "Macro Research",
        "objective": "Macro Impact Assessment",
        "description": "Rates, inflation, oil, recession, policy, FX, growth regimes.",
    },
    "portfolio_research": {
        "label": "Portfolio Research",
        "objective": "Allocation Decision",
        "description": "Add/remove, diversification, rebalancing, portfolio risk.",
    },
    "company_comparison": {
        "label": "Company Comparison",
        "objective": "Relative Company Evaluation",
        "description": "Company A vs Company B (or more) head-to-head.",
    },
    "screening": {
        "label": "Screening",
        "objective": "Universe Filter",
        "description": "Best/high/low screens across a universe or sector.",
    },
    "forecast": {
        "label": "Forecast",
        "objective": "Scenario Analysis",
        "description": "Forward outlook, where X will be, multi-year path.",
    },
    "risk": {
        "label": "Risk",
        "objective": "Downside Analysis",
        "description": "Biggest risks, downside, what breaks the thesis.",
    },
    "valuation": {
        "label": "Valuation",
        "objective": "Fair Value Assessment",
        "description": "Expensive/cheap, fair value, PE vs history (when valuation is the primary ask).",
    },
    "technical": {
        "label": "Technical",
        "objective": "Price Structure Analysis",
        "description": "Breakout, RSI, trend, moving averages, chart structure.",
    },
    "educational": {
        "label": "Educational",
        "objective": "Concept Teaching",
        "description": "Explain/teach finance concepts without security recommendation.",
    },
    "news": {
        "label": "News",
        "objective": "Impact Assessment",
        "description": "Why moved today, latest announcement, earnings summary event.",
    },
}

SECONDARY_INTENTS: dict[str, str] = {
    "valuation": "Valuation lens",
    "risk": "Risk / downside lens",
    "forecast": "Forward-looking / outlook lens",
    "long_term": "Long-term horizon",
    "short_term": "Short-term horizon",
    "portfolio": "Portfolio context",
    "historical_comparison": "Vs history / past regimes",
    "macro": "Macro overlay",
    "peer": "Peer relative",
    "earnings": "Earnings / results focus",
    "technical": "Technical overlay",
    "sector": "Sector overlay",
    "index": "Index overlay",
    "news": "News / event overlay",
    "educational": "Teaching overlay",
}

ENTITY_TYPES: tuple[str, ...] = (
    "Company",
    "Sector",
    "Index",
    "ETF",
    "Commodity",
    "Currency",
    "Bond",
    "Country",
    "Macro Variable",
    "Theme",
    "Portfolio",
    "Watchlist",
    "Person",
    "Event",
    "Unknown",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question_type",
    "primary_intent",
    "secondary_intents",
    "entity",
    "entity_type",
    "research_objective",
    "confidence",
    "requires_clarification",
    "possible_matches",
    "next_stage",
    "executed_layers",
    "executed_analysts",
)

BENCHMARK_QUESTIONS: tuple[str, ...] = (
    "Should I buy HDFC Bank?",
    "Is Nifty IT expensive versus history?",
    "Compare TCS vs Infosys.",
    "What happens if RBI cuts rates?",
    "Explain ROIC.",
    "Should I add Reliance to my portfolio?",
    "Best FMCG companies with high ROIC.",
    "Summarise today's Infosys earnings.",
)

NEXT_STAGE_CLASSIFY_ONLY = "sprint1_classify_only"
NEXT_STAGE_CLARIFY = "clarification_engine"
NEXT_STAGE_BLOCKED = "blocked_pending_clarification"


def intent_label(intent_id: str) -> str:
    row = PRIMARY_INTENTS.get(intent_id) or {}
    return str(row.get("label") or intent_id)


def intent_objective(intent_id: str) -> str:
    row = PRIMARY_INTENTS.get(intent_id) or {}
    return str(row.get("objective") or "Unspecified")


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": RQ1_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "law": "Classify research type before any analyst or intelligence layer executes.",
        "primary_intents": PRIMARY_INTENTS,
        "secondary_intents": SECONDARY_INTENTS,
        "entity_types": list(ENTITY_TYPES),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "benchmark_questions": list(BENCHMARK_QUESTIONS),
        "no_layer_execution": NO_LAYER_EXECUTION,
        "no_analyst_execution": NO_ANALYST_EXECUTION,
        "not_a_top_level_intelligence_layer": True,
    }
