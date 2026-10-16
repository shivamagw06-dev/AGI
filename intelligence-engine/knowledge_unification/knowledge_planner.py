"""Module 3 — Knowledge Planner (ordered provider plan, never blind retrieval)."""

from __future__ import annotations

from knowledge_unification.registry import KnowledgeRegistry, get_registry
from knowledge_unification.schema import KnowledgePlan, QueryPlan

# Default ordered menus by question family. Priority numbers on ProviderSpec
# still decide final sort among the selected set.
_COMPANY_MENU = (
    "company_memory",
    "ikl",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
    "hedge_fund_screens",
)
# Phase 3.0.5 — BI first for company business questions, then CapIQ / memory / KF.
# Phase 3.1.5 — Industry Intelligence consulted so BI can fuse Industry DNA.
_BUSINESS_MENU = (
    "business_intelligence",
    "industry_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Phase 3.2.5 — Investment Intelligence first for investment-shaped questions.
# INV consumes BI + Industry DNA conceptually; planner still consults BI/II.
_INVESTMENT_MENU = (
    "investment_intelligence",
    "hedge_fund_screens",
    "business_intelligence",
    "industry_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Phase 3.3.5 — Portfolio Intelligence for portfolio-shaped questions.
_PORTFOLIO_MENU = (
    "portfolio_intelligence",
    "investment_intelligence",
    "business_intelligence",
    "industry_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Phase 3.4.5 — Research Intelligence for institutional research / document memory.
_RESEARCH_MENU = (
    "research_intelligence_engine",
    "forecast_intelligence_engine",
    "research_intelligence",
    "investment_intelligence",
    "business_intelligence",
    "industry_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Phase 8.5 — Forecast Intelligence Engine for forward outlook / scenarios.
_FORECAST_MENU = (
    "forecast_intelligence_engine",
    "macro_intelligence_engine",
    "research_intelligence_engine",
    "historical_valuation_intelligence",
    "unified_valuation_engine",
    "valuation_attribution_engine",
    "research_intelligence",
    "investment_intelligence",
    "business_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Phase 9.0 — Macro Intelligence Engine for top-down environment / sector transmission.
_MACRO_MENU = (
    "macro_intelligence_engine",
    "market_intelligence_engine",
    "forecast_intelligence_engine",
    "research_intelligence_engine",
    "investment_intelligence",
    "business_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
    "cgl",
    "legacy_kip",
)
# Pure industry / KPI / valuation pedagogy — II first (canonical Industry DNA).
_INDUSTRY_CONCEPT_MENU = (
    "industry_intelligence",
    "business_intelligence",
    "knowledge_factory",
    "financial_concepts",
    "cgl",
    "legacy_kip",
)
_CONCEPT_MENU = (
    "financial_concepts",
    "financial_foundations",
    "financial_statement_intelligence",
    "academy",
)
_ACCOUNTING_MENU = (
    "financial_foundations",
    "financial_statement_warehouse",
    "financial_statement_intelligence",
    "financial_concepts",
    "academy",
)
_VALUATION_MENU = (
    "unified_valuation_engine",
    "historical_valuation_intelligence",
    "valuation_attribution_engine",
    "valuation_policy_engine",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "research_intelligence_engine",
    "financial_statement_warehouse",
    "hedge_fund_screens",
    "financial_concepts",
    "capiq_ikt",
    "company_memory",
)
# Full institutional company / IC-style intelligence — RIE leads; engines under it.
_COMPANY_INTEL_MENU = (
    "research_intelligence_engine",
    "forecast_intelligence_engine",
    "macro_intelligence_engine",
    "unified_valuation_engine",
    "historical_valuation_intelligence",
    "valuation_attribution_engine",
    "valuation_policy_engine",
    "market_intelligence_engine",
    "business_intelligence",
    "industry_intelligence",
    "investment_intelligence",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "financial_statement_warehouse",
    "hedge_fund_screens",
    "capiq_ikt",
    "company_memory",
    "ikl",
    "knowledge_factory",
)
# Premium / discount attribution — VARIE + HVIE + VPAE first.
_ATTRIBUTION_MENU = (
    "valuation_attribution_engine",
    "historical_valuation_intelligence",
    "valuation_policy_engine",
    "unified_valuation_engine",
    "research_intelligence_engine",
    "forecast_intelligence_engine",
    "macro_intelligence_engine",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_consensus",
    "valuation_terminal",
    "capiq_ikt",
    "company_memory",
)
# Own-history / regime questions — HVIE first.
_HISTORICAL_VAL_MENU = (
    "historical_valuation_intelligence",
    "valuation_attribution_engine",
    "unified_valuation_engine",
    "valuation_policy_engine",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_terminal",
    "valuation_consensus",
    "research_intelligence_engine",
    "capiq_ikt",
)
# Hedge-fund / factor screens across the universe.
_SCREEN_MENU = (
    "hedge_fund_screens",
    "forecast_intelligence_engine",
    "research_intelligence_engine",
    "unified_valuation_engine",
    "valuation_attribution_engine",
    "historical_valuation_intelligence",
    "market_intelligence_engine",
    "institutional_warehouse",
    "valuation_terminal",
    "valuation_consensus",
    "investment_intelligence",
)
# Cross-company institutional comparison.
# BI + CapIQ/memory early so evidence_fusion survives max_providers budgets.
_COMPARE_MENU = (
    "business_intelligence",
    "industry_intelligence",
    "capiq_ikt",
    "company_memory",
    "knowledge_factory",
    "research_intelligence_engine",
    "unified_valuation_engine",
    "historical_valuation_intelligence",
    "valuation_attribution_engine",
    "forecast_intelligence_engine",
    "valuation_policy_engine",
    "institutional_warehouse",
    "valuation_terminal",
    "valuation_consensus",
    "financial_statement_warehouse",
    "ikl",
)
# Today's market / breadth / flows / rotation.
_MARKET_MENU = (
    "market_intelligence_engine",
    "macro_intelligence_engine",
    "historical_valuation_intelligence",
    "institutional_warehouse",
    "forecast_intelligence_engine",
    "valuation_terminal",
    "hedge_fund_screens",
)
# Sell-side consensus (CapIQ targets / broker counts / coverage) leads, then
# AGI's own layers so the answer can separate market view from AGI view.
_CONSENSUS_MENU = (
    "valuation_consensus",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_terminal",
    "financial_statement_warehouse",
    "capiq_ikt",
    "investment_intelligence",
    "business_intelligence",
    "company_memory",
    "industry_intelligence",
    "ikl",
)
# Universe-wide consensus screens name no company — consulting the company
# engines only yields "Business type: unknown" noise.
_CONSENSUS_SCREEN_MENU = (
    "valuation_consensus",
    "historical_intelligence",
    "institutional_warehouse",
    "valuation_terminal",
    "financial_statement_warehouse",
    "industry_intelligence",
)
# Industry-specific valuation pedagogy (P/B for banks, EV/Sales for SaaS, …).
_VALUATION_INDUSTRY_MENU = (
    "industry_intelligence",
    "financial_concepts",
    "business_intelligence",
    "academy",
)

_BUSINESS_TYPES = frozenset(
    {
        "business_model",
        "moat",
        "unit_economics",
        "comparison",
        "business_risk",
        "industry",
    }
)


def build_knowledge_plan(
    query: QueryPlan,
    *,
    registry: KnowledgeRegistry | None = None,
) -> KnowledgePlan:
    reg = registry or get_registry()
    types = set(query.question_types)
    selected: list[str] = []
    rationale: list[str] = []

    business_shaped = bool(types.intersection(_BUSINESS_TYPES))
    company_bound = bool(query.ticker_hint or query.company_hint or "comparison" in types)
    qlow = (query.question or "").lower()
    research_shaped = "research" in types or any(
        k in qlow
        for k in (
            "annual report",
            "earnings call",
            "earnings transcript",
            "conference call",
            "transcript",
            "management commentary",
            "management intelligence",
            "guidance history",
            "guidance evolved",
            "guidance intelligence",
            "research memory",
            "deep research",
            "cross-document",
            "cross document",
            "investor day",
            "research timeline",
            "timeline intelligence",
            "what changed since",
            "last quarter",
            "five years of",
            "5 years of",
            "from the annual report",
            "capital allocation evolution",
            "management philosophy",
            "estimate intelligence",
            "estimate changes",
            "event intelligence",
            "event research",
            "complete research",
            "research note",
            "research dossier",
        )
    )
    company_intel_shaped = any(
        k in qlow
        for k in (
            "institutional equity analyst",
            "complete company intelligence",
            "company intelligence",
            "investment committee",
            "ic report",
            "committee report",
            "research report",
            "as if you were",
            "preparing an investment",
            "full research",
            "dossier",
            "institutional profile",
            "key monitoring points",
            "top five factors",
            "observed, derived, and inferred",
            "observed, derived and inferred",
        )
    )
    attribution_shaped = "attribution" in types or any(
        k in qlow
        for k in (
            "attribute",
            "attribution",
            "trades at a premium",
            "trading at a premium",
            "trades at a discount",
            "trading at a discount",
            "premium valuation",
            "why .+ premium",
            "break down the premium",
            "decompose",
            "what explains the",
            "valuation driver",
            "what drives valuation",
        )
    )
    # Regex-lite: "why ... premium" already covered via substring "premium" + why.
    if not attribution_shaped and "premium" in qlow and any(
        k in qlow for k in ("why", "explain", "break down", "because", "driven")
    ):
        attribution_shaped = True
    historical_val_shaped = "historical" in types or any(
        k in qlow
        for k in (
            "own history",
            "historical valuation",
            "historically",
            "traded at valuations similar",
            "similar to today",
            "when has",
            "when was",
            "ever traded",
            "cheapest",
            "percentile",
            "unusual",
            "relative to its own history",
            "versus history",
            "vs history",
            "what happened afterwards",
        )
    )
    screen_shaped = "screen" in types or any(
        k in qlow
        for k in (
            "hedge fund",
            "find high-quality",
            "find companies",
            "screen for",
            "which stocks",
            "which companies",
            "compounders",
            "strategy screen",
            "factor screen",
            "rising institutional ownership",
            "attractive valuation",
            "qualify",
        )
    ) and not company_bound
    market_shaped = "market_summary" in types or any(
        k in qlow
        for k in (
            "today's indian market",
            "today's market",
            "summarize today's",
            "market summary",
            "market breadth",
            "sector rotation",
            "institutional flows",
            "most important developments",
            "indian market",
        )
    ) and not company_bound
    comparison_shaped = "comparison" in types or any(
        k in qlow for k in ("compare", " versus ", " vs ", " vs.", "stronger institutional")
    )
    portfolio_shaped = "portfolio" in types or any(
        k in qlow
        for k in (
            "portfolio construction",
            "portfolio quality",
            "portfolio scenario",
            "risk budget",
            "factor exposure",
            "position sizing",
            "rebalanc",
            "agib core",
            "concentrated growth",
            "watchlist",
        )
    )
    macro_shaped = "macro" in types or any(
        k in qlow
        for k in (
            "macro regime",
            "macro environment",
            "macro outlook",
            "macro exposure",
            "economic cycle",
            "interest rates affecting",
            "falling inflation",
            "liquidity environment",
            "which sectors benefit",
            "which sectors are likely",
            "how does oil",
            "why has the macro",
            "india's economic cycle",
            "current macro",
            "rbi policy",
            "rbi rate",
            "repo rate",
            "basis point",
            "rate cut",
            "rate hike",
            "affect indian banks",
            "nbfcs",
        )
    )
    forecast_shaped = "forecast" in types or any(
        k in qlow
        for k in (
            "forecast",
            "outlook",
            "bull case",
            "bear case",
            "base case",
            "bull, base, and bear",
            "bull, base and bear",
            "next 3 years",
            "next 3–5 years",
            "next 3-5 years",
            "3–5 years",
            "3-5 years",
            "fy+",
            "fy+1",
            "fy+2",
            "fy+3",
            "assumptions matter",
            "confidence low",
            "invalidate this forecast",
            "how has the forecast",
            "sensitivity",
            "scenario probabilities",
            "forecast scenarios",
            "forecast confidence",
        )
    )
    investment_shaped = "investment" in types or any(
        k in qlow
        for k in (
            "investment thesis",
            "catalyst",
            "scenario analysis",
            "bull and bear",
            "bear case",
            "base scenario",
            "scenario",
            "downside",
            "investors monitor",
            "for an investor",
            "monitoring priorit",
            "monitoring point",
            "evidence strength",
            "from an investment",
            "investment quality",
            "investment risk",
            "investment case",
            "committee",
            "what drives valuation",
            "valuation driver",
            "quality perspective",
            "business quality",
            "unknowns remain",
            "allocate capital",
            "capital allocation",
            "roic improve",
            "why might roic",
        )
    )
    industry_pedagogy = bool(
        types.intersection({"industry", "unit_economics", "business_risk"})
        or (
            "valuation" in types
            and not company_bound
            and any(
                tok in (query.question or "").lower()
                for tok in (
                    "bank",
                    "saas",
                    "software",
                    "airline",
                    "fmcg",
                    "utilit",
                    "hospital",
                    "telecom",
                    "insurance",
                    "insurer",
                    "cement",
                    "real estate",
                    "commodity",
                    "p/b",
                    "ev/sales",
                    "embedded value",
                    "nav",
                )
            )
        )
    )

    if "consensus" in types and company_bound:
        selected.extend(_CONSENSUS_MENU)
        rationale.append(
            "Consensus-shaped → Valuation Consensus (CapIQ market data) → CapIQ profile → AGI layers."
        )
    elif "consensus" in types:
        selected.extend(_CONSENSUS_SCREEN_MENU)
        rationale.append(
            "Consensus screen (no company bind) → Valuation Consensus universe → Industry DNA."
        )
    elif market_shaped:
        selected.extend(_MARKET_MENU)
        rationale.append(
            "Market-summary → Market Intelligence → MIE → HVIE → warehouse (no vendor crawl)."
        )
    elif macro_shaped and not company_bound:
        selected.extend(_MACRO_MENU)
        rationale.append(
            "Macro-shaped → MIE → FIE → RIE → INV → BI (top-down context, no recalculation)."
        )
    elif screen_shaped:
        selected.extend(_SCREEN_MENU)
        rationale.append(
            "Screen-shaped → Hedge Fund Factors/screens → FIE → RIE → UVE/VARIE/HVIE."
        )
    elif company_intel_shaped and company_bound:
        selected.extend(_COMPANY_INTEL_MENU)
        rationale.append(
            "Company-intelligence / IC → RIE → FIE → MIE → UVE/HVIE/VARIE/VPAE → warehouse."
        )
    elif attribution_shaped and company_bound:
        selected.extend(_ATTRIBUTION_MENU)
        rationale.append(
            "Attribution-shaped → VARIE → HVIE → VPAE → UVE → RIE/FIE/MIE."
        )
    elif historical_val_shaped and company_bound:
        selected.extend(_HISTORICAL_VAL_MENU)
        rationale.append(
            "Historical-valuation → HVIE → VARIE → UVE → VPAE → warehouse."
        )
    elif forecast_shaped and company_bound:
        selected.extend(_FORECAST_MENU)
        rationale.append(
            "Forecast-shaped → FIE → MIE → RIE → warehouse/valuation layers (no recalculation)."
        )
    elif comparison_shaped and (company_bound or business_shaped):
        selected.extend(_COMPARE_MENU)
        rationale.append(
            "Comparison → BI/Industry + CapIQ/memory → RIE → UVE/HVIE/VARIE/FIE."
        )
    elif research_shaped and (company_bound or "research" in types or "comparison" in types):
        selected.extend(_RESEARCH_MENU)
        rationale.append(
            "Research-shaped → Research Intelligence → INV → BI → Industry DNA → CapIQ → memory → KF."
        )
    elif portfolio_shaped:
        selected.extend(_PORTFOLIO_MENU)
        rationale.append(
            "Portfolio-shaped → Portfolio Intelligence → INV → BI → Industry DNA → CapIQ → memory → KF."
        )
    elif investment_shaped and (company_bound or "comparison" in types or "investment" in types):
        selected.extend(_INVESTMENT_MENU)
        rationale.append(
            "Investment-shaped → Investment Intelligence → BI → Industry DNA → CapIQ → memory → KF."
        )
    elif business_shaped and company_bound:
        selected.extend(_BUSINESS_MENU)
        rationale.append(
            "Business-shaped + company → BI → Industry DNA → CapIQ → memory → KF → CGL → legacy."
        )
    elif business_shaped or (industry_pedagogy and not company_bound):
        # Industry / unit-economics / KPI / valuation pedagogy without a ticker bind.
        selected.extend(_INDUSTRY_CONCEPT_MENU)
        rationale.append(
            "Industry pedagogy (no company bind) → Industry Intelligence → BI → KF → concepts."
        )
    elif types.intersection({"company", "market", "news"}) and (
        query.ticker_hint or query.company_hint
    ):
        selected.extend(_COMPANY_MENU)
        rationale.append("Company-shaped question → memory → CapIQ → KF → CGL → legacy fallback.")

    if (
        types.intersection({"concept"})
        and not query.ticker_hint
        and not business_shaped
        and not industry_pedagogy
        and not macro_shaped
        and not market_shaped
        and not screen_shaped
        and not forecast_shaped
    ):
        selected.extend(_CONCEPT_MENU)
        rationale.append("Concept question → deterministic finance engines only (no retrieval default).")

    if types.intersection({"accounting", "financial_statement"}):
        selected.extend(_ACCOUNTING_MENU)
        rationale.append("Accounting/FSA → foundations + statement intelligence.")

    if types.intersection({"valuation"}) and not business_shaped and not attribution_shaped and not historical_val_shaped:
        if industry_pedagogy and not company_bound:
            selected.extend(_VALUATION_INDUSTRY_MENU)
            rationale.append("Industry valuation pedagogy → Industry Intelligence → concepts.")
        else:
            selected.extend(_VALUATION_MENU)
            rationale.append(
                "Valuation → UVE/HVIE/VARIE/VPAE → warehouse/consensus (company-bound)."
            )

    if macro_shaped and company_bound and "macro_intelligence_engine" not in selected:
        # Company + macro exposure: append MIE without replacing the company menu.
        selected.extend(_MACRO_MENU[:4])
        rationale.append("Company + macro exposure → append MIE/FIE context.")

    if not selected:
        # Unknown: try concepts then soft company detection leftovers, then legacy.
        selected = ["financial_concepts", "financial_foundations", "capiq_ikt", "legacy_kip"]
        rationale.append("Unknown intent → conservative deterministic-first menu.")

    # Drop providers that are hard-empty/error when health is known, but keep
    # them if health is unknown (lazy). Refresh lightly.
    health = reg.refresh_health()
    filtered = []
    for pid in selected:
        if pid not in {p.spec.id for p in reg.all()}:
            continue
        status = health.get(pid, "unknown")
        if status == "error":
            rationale.append(f"Skipped {pid}: health=error.")
            continue
        # Keep "empty" providers in the plan so diagnostics show they were
        # considered; ranking will reject empty results after consult.
        filtered.append(pid)

    # Preserve menu order — menus encode the Knowledge Dependency Map
    # (Industry DNA → BI → CapIQ → …). Re-sorting by ProviderSpec.priority
    # would incorrectly put Industry Intelligence ahead of BI on company
    # business questions.
    seen = set()
    unique = []
    for pid in filtered:
        if pid not in seen:
            seen.add(pid)
            unique.append(pid)

    return KnowledgePlan(query=query, provider_ids=unique, rationale=rationale)
