"""Universal Knowledge Planner — every question gets one execution plan.

The planner decides which providers to consult. It never hardcodes a route.
KUL's knowledge_planner owns menu selection by question family; this layer
adds expected-provider contracts so coverage can detect silence.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from universal_knowledge.registry import CAPABILITIES, DEPENDENCY_ORDER, capability


_EXPECTED: dict[str, tuple[str, ...]] = {
    "valuation": (
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "valuation_policy_engine",
        "valuation_terminal",
        "valuation_consensus",
        "institutional_warehouse",
        "industry_intelligence",
    ),
    "attribution": (
        "valuation_attribution_engine",
        "historical_valuation_intelligence",
        "valuation_policy_engine",
        "unified_valuation_engine",
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
    ),
    "historical": (
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "unified_valuation_engine",
        "valuation_policy_engine",
        "historical_intelligence",
        "institutional_warehouse",
    ),
    "forecast": (
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
        "research_intelligence_engine",
        "historical_valuation_intelligence",
        "unified_valuation_engine",
        "institutional_warehouse",
    ),
    "macro": (
        "macro_intelligence_engine",
        "market_intelligence_engine",
        "forecast_intelligence_engine",
        "research_intelligence_engine",
        "institutional_warehouse",
    ),
    "market": (
        "market_intelligence_engine",
        "macro_intelligence_engine",
        "historical_valuation_intelligence",
        "institutional_warehouse",
        "hedge_fund_screens",
    ),
    "company_intel": (
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "valuation_policy_engine",
        "market_intelligence_engine",
        "institutional_warehouse",
        "business_intelligence",
    ),
    "consensus": (
        "valuation_consensus",
        "capiq_ikt",
        "valuation_terminal",
    ),
    "business": (
        "business_intelligence",
        "industry_intelligence",
        "capiq_ikt",
        "company_memory",
    ),
    "investment": (
        "research_intelligence_engine",
        "investment_intelligence",
        "business_intelligence",
        "industry_intelligence",
        "unified_valuation_engine",
        "valuation_terminal",
        "valuation_consensus",
        "hedge_fund_screens",
    ),
    "portfolio": (
        "portfolio_intelligence",
        "investment_intelligence",
        "valuation_terminal",
    ),
    "research": (
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "research_intelligence",
        "company_memory",
        "valuation_consensus",
        "institutional_warehouse",
    ),
    "financials": (
        "financial_statement_warehouse",
        "financial_statement_intelligence",
        "capiq_ikt",
        "valuation_terminal",
    ),
    "accounting": (
        "financial_foundations",
        "financial_statement_intelligence",
        "financial_concepts",
    ),
    "industry": (
        "industry_intelligence",
        "business_intelligence",
        "financial_concepts",
    ),
    "company": (
        "research_intelligence_engine",
        "institutional_warehouse",
        "capiq_ikt",
        "company_memory",
        "business_intelligence",
        "industry_intelligence",
        "unified_valuation_engine",
        "valuation_terminal",
        "valuation_consensus",
    ),
    "concept": (
        "financial_concepts",
        "financial_foundations",
        "academy",
    ),
    "screen": (
        "hedge_fund_screens",
        "forecast_intelligence_engine",
        "research_intelligence_engine",
        "unified_valuation_engine",
        "valuation_attribution_engine",
        "market_intelligence_engine",
        "institutional_warehouse",
    ),
    "comparison": (
        "research_intelligence_engine",
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "forecast_intelligence_engine",
        "business_intelligence",
        "institutional_warehouse",
    ),
}


_FAMILY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("screen", re.compile(
        r"\b(screen|scanner|hedge fund|long/?short|market neutral|pair trade|"
        r"value trap|momentum|quality screen|compounders?|find (?:high-quality|companies)|"
        r"which (?:stocks|companies))\b", re.I)),
    # Full IC / research memoranda beat incidental "business model" section lists.
    ("company_intel", re.compile(
        r"\b(institutional equity analyst|complete company intelligence|"
        r"investment committee|ic (?:report|memorandum)|committee (?:report|memorandum)|"
        r"research report|research memorandum|as if you were|"
        r"preparing an investment|dossier|key monitoring points|"
        r"observed,? derived,? and inferred)\b", re.I)),
    ("forecast", re.compile(
        r"\b(forecast|outlook|bull case|bear case|base case|"
        r"next 3(?:\s*[–-]\s*5)? years|scenario probabilities)\b", re.I)),
    ("market", re.compile(
        r"\b(today'?s (?:indian )?market|market summary|market breadth|"
        r"sector rotation|institutional flows)\b", re.I)),
    # Moat / premium-pricing business questions must win over valuation attribution.
    ("business", re.compile(
        r"\b(business model|what does .+ do|explain .{0,40}do|moat|"
        r"competes?|unit economics|switching costs?|pricing power|"
        r"sustain(?:s|ed|ing)? premium pricing|premium pricing|"
        r"competitive advantages?|membership model)\b", re.I)),
    # Attribution / premium decomposition must win over incidental "macro factors"
    # mentions inside company valuation questions (HDFC premium, etc.).
    # Do not steal moat/pricing-power questions ("sustain premium pricing").
    ("attribution", re.compile(
        r"\b(attribute|attribution|break down the premium|decompose|"
        r"trades? at a premium|trading at a premium|premium to peers|"
        r"premium valuation|"
        r"why .{0,40}(?:trades? at a |trading at a |valued at a )?premium"
        r"(?! pricing))\b", re.I)),
    # Explicit compare / expensive-cheap must win over "historical valuation"
    # mentions that appear as section lists inside those questions.
    ("comparison", re.compile(
        r"\b(compare|versus|\bvs\.?\b|stronger institutional profile)\b", re.I)),
    ("valuation", re.compile(
        r"\b(expensive or cheap|currently (?:expensive|cheap)|overvalued|undervalued|"
        r"cheap relative|expensive relative)\b", re.I)),
    ("historical", re.compile(
        r"\b(historical valuation|own history|similar to today|when has|"
        r"what happened afterwards|versus history|vs\.? history|ever traded)\b", re.I)),
    # Avoid bare \bmacro\b — "macro exposure/factors" appear inside company IC
    # and attribution questions and must not steal those families.
    ("macro", re.compile(
        r"\b(rbi|repo rate|rate cut|rate hike|basis point|"
        r"interest rates?|inflation|which sectors (?:benefit|are likely)|nbfc|"
        r"macro (?:regime|outlook|environment|backdrop|impact|transmission|"
        r"conditions?|question|view|analysis))\b", re.I)),
    ("consensus", re.compile(
        r"\b(consensus|target price|price target|analysts? cover|coverage|"
        r"rating split|upside)\b", re.I)),
    ("valuation", re.compile(
        r"\b(expensive|cheap|overvalued|undervalued|valuation|multiple|"
        r"p/?e\b|p/?b\b|ev/?ebitda|price to (?:earnings|book|sales)|"
        r"trades? at|re-?rat(?:e|ing)|de-?rat(?:e|ing)|discount|"
        r"(?<!pricing )(?<!sustain )(?<!sustains )(?<!sustaining )premium)\b", re.I)),
    ("financials", re.compile(
        r"\b(revenue|eps|earnings|margin|debt|cash flow|fcf|capex|"
        r"balance sheet|income statement|working capital)\b", re.I)),
    ("accounting", re.compile(
        r"\b(accrual|cash profit|journal|ledger|debit|credit|gaap|ind.?as|"
        r"depreciation|amortisation|amortization|impairment)\b", re.I)),
    ("investment", re.compile(
        r"\b(investment thesis|why (?:would|should).{0,20}own|thesis|catalysts?|"
        r"biggest risks?|business and financial quality)\b", re.I)),
    ("research", re.compile(
        r"\b(annual report|earnings call|transcript|guidance|"
        r"management (?:said|commentary)|what changed)\b", re.I)),
    ("portfolio", re.compile(
        r"\b(portfolio|position sizing|allocation|gross exposure|net exposure)\b", re.I)),
    ("industry", re.compile(
        r"\b(industry|sector|how (?:are|is) .{0,30} valued|banking valuation|"
        r"valu(?:e|ing) (?:a |an )?(?:bank|saas|nbfc))\b", re.I)),
    ("concept", re.compile(
        r"\b(what is|define|difference between|explain the)\b", re.I)),
)


def detect_family(question: str, *, question_type: Optional[str] = None) -> str:
    q = str(question or "")
    for family, pattern in _FAMILY_PATTERNS:
        if pattern.search(q):
            return family
    if question_type in _EXPECTED:
        return question_type  # type: ignore[return-value]
    if question_type in {"business_model", "moat", "unit_economics"}:
        return "business"
    return "company"


def expected_providers(family: str) -> list[str]:
    return list(_EXPECTED.get(family, _EXPECTED["company"]))


def plan(
    question: str,
    *,
    ticker: Optional[str] = None,
    question_type: Optional[str] = None,
    max_providers: int = 10,
) -> dict[str, Any]:
    """Build the universal execution plan for one question."""
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.knowledge_planner import build_knowledge_plan

    family = detect_family(question, question_type=question_type)
    expected = expected_providers(family)

    query = plan_query(question)
    if ticker and not query.ticker_hint:
        query.ticker_hint = str(ticker).upper()
    if ticker and query.ticker_hint and "company" not in query.question_types:
        query.question_types = ["company", *list(query.question_types)]
    # Stamp the detected family onto question_types so KUL menus fire correctly
    # even when the query planner classified the question as pure industry pedagogy.
    family_type = {
        "valuation": "valuation",
        "attribution": "attribution",
        "historical": "historical",
        "forecast": "forecast",
        "macro": "macro",
        "market": "market_summary",
        "company_intel": "research",
        "comparison": "comparison",
        "consensus": "consensus",
        "business": "business_model",
        "investment": "investment",
        "portfolio": "portfolio",
        "research": "research",
        "financials": "financial_statement",
        "accounting": "accounting",
        "industry": "industry",
        "screen": "screen",
    }.get(family)
    if family_type and family_type not in query.question_types:
        query.question_types = [family_type, *list(query.question_types)]

    knowledge = build_knowledge_plan(query)
    menu = list(knowledge.provider_ids or [])

    # Expected providers are never truncated — coverage requires the attempt.
    # Preserve KUL menu order for institutional showcase families so RIE/FIE/MIE/
    # UVE/HVIE/VARIE are not pushed behind pedagogy by role-sort.
    locked = [pid for pid in expected if pid in CAPABILITIES]
    extras = [pid for pid in menu if pid not in locked]
    preserve_menu = family in {
        "valuation", "attribution", "historical", "forecast", "macro", "market",
        "company_intel", "comparison", "screen", "research", "investment",
    }
    budget = max(len(locked), int(max_providers), 14 if preserve_menu else int(max_providers))
    if preserve_menu:
        # Menu order first (already encodes Knowledge Dependency Map for the family),
        # then any locked expected providers not already present.
        ordered: list[str] = []
        seen: set[str] = set()
        for pid in list(menu) + locked:
            if pid in seen:
                continue
            seen.add(pid)
            ordered.append(pid)
            if len(ordered) >= budget:
                break
        selected = ordered
    else:
        role_rank = {role: i for i, role in enumerate(DEPENDENCY_ORDER)}

        def sort_key(pid: str) -> tuple[int, int, str]:
            cap = capability(pid)
            if cap is None:
                return (99, 99, pid)
            return (role_rank.get(cap.role, 50), cap.priority, pid)

        selected = sorted(set(locked + extras[: max(0, budget - len(locked))]), key=sort_key)
    knowledge.provider_ids = selected

    return {
        "ok": True,
        "engine": "universal_knowledge_planner",
        "version": "uko-6.0",
        "question": question,
        "ticker": query.ticker_hint,
        "family": family,
        "question_types": list(query.question_types),
        "selected_providers": selected,
        "expected_providers": expected,
        "query_plan": query,
        "knowledge_plan": knowledge,
        "max_providers": max_providers,
    }
