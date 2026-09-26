"""Fixed engine priorities per question family — consensus never leads."""

from __future__ import annotations

from typing import Optional

# (primary, secondary..., supporting..., reference...)
FAMILY_PRIORITY: dict[str, dict[str, tuple[str, ...]]] = {
    "company": {
        "primary": ("research_intelligence_engine",),
        # Business narrative before thin FIE scenario dumps for IC memoranda.
        "secondary": ("business_intelligence", "investment_intelligence"),
        "supporting": (
            "forecast_intelligence_engine",
            "valuation_attribution_engine",
            "historical_valuation_intelligence",
            "unified_valuation_engine",
            "macro_intelligence_engine",
            "valuation_policy_engine",
            "market_intelligence_engine",
            "industry_intelligence",
            "historical_intelligence",
            "institutional_warehouse",
            "valuation_terminal",
        ),
        "reference": ("valuation_consensus", "capiq_ikt"),
    },
    "company_intel": {
        "primary": ("research_intelligence_engine",),
        "secondary": ("business_intelligence", "investment_intelligence"),
        "supporting": (
            "forecast_intelligence_engine",
            "valuation_attribution_engine",
            "historical_valuation_intelligence",
            "unified_valuation_engine",
            "macro_intelligence_engine",
            "valuation_policy_engine",
            "market_intelligence_engine",
            "industry_intelligence",
            "historical_intelligence",
            "institutional_warehouse",
            "valuation_terminal",
        ),
        "reference": ("valuation_consensus", "capiq_ikt"),
    },
    "valuation": {
        "primary": ("unified_valuation_engine",),
        "secondary": ("historical_valuation_intelligence",),
        "supporting": (
            "valuation_attribution_engine",
            "valuation_policy_engine",
            "valuation_terminal",
            "historical_intelligence",
            "institutional_warehouse",
        ),
        "reference": ("valuation_consensus", "capiq_ikt"),
    },
    "historical": {
        "primary": ("historical_valuation_intelligence",),
        "secondary": ("valuation_attribution_engine",),
        "supporting": (
            "unified_valuation_engine",
            "valuation_policy_engine",
            "historical_intelligence",
            "valuation_terminal",
        ),
        "reference": ("valuation_consensus",),
    },
    "forecast": {
        "primary": ("forecast_intelligence_engine",),
        "secondary": ("research_intelligence_engine",),
        "supporting": (
            "macro_intelligence_engine",
            "historical_valuation_intelligence",
            "unified_valuation_engine",
            "investment_intelligence",
            "business_intelligence",
        ),
        "reference": ("valuation_consensus",),
    },
    "macro": {
        "primary": ("macro_intelligence_engine",),
        "secondary": ("market_intelligence_engine",),
        "supporting": ("forecast_intelligence_engine", "research_intelligence_engine"),
        "reference": ("valuation_consensus",),
    },
    "market": {
        "primary": ("market_intelligence_engine",),
        "secondary": ("macro_intelligence_engine",),
        "supporting": (
            "historical_valuation_intelligence",
            "institutional_warehouse",
            "hedge_fund_screens",
            "valuation_terminal",
        ),
        "reference": (),
    },
    "comparison": {
        "primary": ("research_intelligence_engine",),
        "secondary": (
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "forecast_intelligence_engine",
        ),
        "supporting": (
            "business_intelligence",
            "industry_intelligence",
            "valuation_policy_engine",
            "institutional_warehouse",
        ),
        "reference": ("valuation_consensus", "capiq_ikt"),
    },
    "compare": {
        "primary": ("research_intelligence_engine",),
        "secondary": (
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "forecast_intelligence_engine",
        ),
        "supporting": (
            "business_intelligence",
            "industry_intelligence",
            "valuation_policy_engine",
        ),
        "reference": ("valuation_consensus",),
    },
    "screen": {
        "primary": ("hedge_fund_screens",),
        "secondary": (),
        "supporting": (
            "forecast_intelligence_engine",
            "research_intelligence_engine",
            "unified_valuation_engine",
            "valuation_attribution_engine",
            "market_intelligence_engine",
            "institutional_warehouse",
        ),
        "reference": ("valuation_consensus",),
    },
    "hedge_fund": {
        "primary": ("hedge_fund_screens",),
        "secondary": (),
        "supporting": (
            "forecast_intelligence_engine",
            "research_intelligence_engine",
            "unified_valuation_engine",
            "valuation_attribution_engine",
        ),
        "reference": (),
    },
    "attribution": {
        "primary": ("valuation_attribution_engine",),
        "secondary": ("historical_valuation_intelligence",),
        "supporting": (
            "valuation_policy_engine",
            "unified_valuation_engine",
            "research_intelligence_engine",
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
        ),
        "reference": ("valuation_consensus",),
    },
    "research": {
        "primary": ("research_intelligence_engine",),
        "secondary": ("forecast_intelligence_engine",),
        "supporting": (
            "investment_intelligence",
            "business_intelligence",
            "historical_intelligence",
            "institutional_warehouse",
        ),
        "reference": ("valuation_consensus", "capiq_ikt"),
    },
    "investment": {
        "primary": ("research_intelligence_engine", "investment_intelligence"),
        "secondary": ("forecast_intelligence_engine",),
        "supporting": (
            "unified_valuation_engine",
            "business_intelligence",
            "hedge_fund_screens",
        ),
        "reference": ("valuation_consensus",),
    },
    # Moat / business-model pedagogy — BI leads; valuation is supporting only.
    "business": {
        "primary": ("business_intelligence",),
        "secondary": ("industry_intelligence", "investment_intelligence"),
        "supporting": (
            "research_intelligence_engine",
            "forecast_intelligence_engine",
            "valuation_attribution_engine",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "capiq_ikt",
            "company_memory",
        ),
        "reference": ("valuation_consensus",),
    },
}


def resolve_family(family: Optional[str], question: str = "") -> str:
    """Map UKO / planner family onto an IFAC priority family.

    Question shape can override a misclassified UKO family (e.g. premium /
    attribution questions that mentioned 'macro factors' and were labelled macro).
    """
    f = str(family or "").strip().lower()
    q = (question or "").lower()
    aliases = {
        "company_intel": "company",
        "compare": "comparison",
        "hedge_fund": "screen",
        "market_summary": "market",
    }
    f = aliases.get(f, f)

    # High-confidence question overrides — applied even when UKO family is set.
    # Full IC memoranda beat incidental "business model" section lists.
    if any(
        k in q
        for k in (
            "investment committee",
            "institutional equity analyst",
            "as if you were",
            "dossier",
            "committee memorandum",
            "research memorandum",
            "preparing an investment",
        )
    ):
        return "company"
    if any(
        k in q
        for k in (
            "break down the premium",
            "trades at a premium",
            "trading at a premium",
            "premium valuation",
            "premium to peers",
            "valuation attribution",
            "trades at a premium valuation",
            "why .* trades at a premium",
        )
    ) or (
        "premium" in q
        and any(k in q for k in ("attribute", "attribution", "break down", "decompose", "why"))
        and "pricing" not in q
    ):
        return "attribution"
    if any(
        k in q
        for k in (
            "moat",
            "pricing power",
            "switching costs",
            "premium pricing",
            "sustain premium",
            "membership model",
            "competitive advantage",
        )
    ) or (
        "business model" in q
        and not any(
            k in q
            for k in (
                "investment committee",
                "memorandum",
                "dossier",
                "monitoring points",
                "observed, derived",
            )
        )
    ):
        return "business"
    if any(k in q for k in ("compare ", " versus ", " vs ", "stronger institutional profile")):
        return "comparison"
    if any(k in q for k in ("expensive or cheap", "currently expensive", "currently cheap", "overvalued", "undervalued")):
        return "valuation"
    if any(k in q for k in ("hedge fund", "compounder", "screen for", "which stocks", "long/short")):
        return "screen"
    if any(k in q for k in ("today's indian market", "market summary", "market breadth", "sector rotation")):
        return "market"
    if any(k in q for k in ("rate cut", "basis point", "rbi", "macro regime", "macro outlook", "which sectors are likely")):
        return "macro"
    if any(k in q for k in ("similar to today", "when has", "what happened afterwards", "versus history", "vs history")):
        return "historical"
    if any(k in q for k in ("bull", "bear", "base case", "next 3–5", "next 3-5", "scenario probabilities")):
        return "forecast"

    if f in FAMILY_PRIORITY:
        return f
    if any(k in q for k in ("outlook", "forecast")):
        return "forecast"
    if any(k in q for k in ("expensive", "cheap", "valuation", "overvalued", "undervalued")):
        return "valuation"
    if f == "business":
        return "business"
    return "company" if f == "company" else (f if f in FAMILY_PRIORITY else "company")


def priority_order(family: str) -> list[str]:
    pack = FAMILY_PRIORITY.get(family) or FAMILY_PRIORITY["company"]
    out: list[str] = []
    for key in ("primary", "secondary", "supporting", "reference"):
        for pid in pack.get(key) or ():
            if pid not in out:
                out.append(pid)
    return out


def primary_ids(family: str) -> tuple[str, ...]:
    pack = FAMILY_PRIORITY.get(family) or FAMILY_PRIORITY["company"]
    return tuple(pack.get("primary") or ())
