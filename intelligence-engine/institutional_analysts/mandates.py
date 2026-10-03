"""Analyst mandates — one question, one domain, explicit inputs/outputs."""

from __future__ import annotations

from typing import Any

# Forbidden vocabulary by role — keeps analysts inside their domain.
# Matched case-insensitively against free-text fields before packaging.
DOMAIN_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "business": (
        r"\bp/?e\b",
        r"\bp/?b\b",
        r"\bmultiple[s]?\b",
        r"\bvaluation\b",
        r"\bintrinsic\b",
        r"\bmargin of safety\b",
        r"\bcheap\b",
        r"\bexpensive\b",
        r"\bovervalued\b",
        r"\bundervalued\b",
        r"\btrading at\b",
        r"\bmomentum\b",
        r"\b52[- ]?week\b",
    ),
    "financial": (
        r"\bbrand\b",
        r"\bmoat\b",
        r"\bcompetitive advantage",
        r"\bbusiness model\b",
        r"\bpricing power\b",
        r"\bfranchise quality\b",
        r"\bp/?e\b",
        r"\bintrinsic\b",
        r"\bmargin of safety\b",
        r"\bmacro\b",
        r"\binflation\b",
        r"\bgdp\b",
    ),
    "valuation": (
        r"\bmoat\b",
        r"\bbrand strength\b",
        r"\bmanagement quality\b",
        r"\bgovernance\b",
        r"\bpromoter\b",
        r"\bmomentum\b",
        r"\bvolume\b",
        r"\bmacro transmission\b",
    ),
    "market": (
        r"\bmoat\b",
        r"\bbusiness model\b",
        r"\bintrinsic value\b",
        r"\bmargin of safety\b",
        r"\broe\b",
        r"\broic\b",
        r"\bgovernance\b",
        r"\binflation\b",
        r"\bgdp\b",
    ),
    "sector": (
        r"\bp/?e\b",
        r"\bintrinsic\b",
        r"\bmargin of safety\b",
        r"\bpromoter holding\b",
        r"\b52[- ]?week\b",
        r"\bmomentum\b",
    ),
    "macro": (
        r"\bmoat\b",
        r"\bbusiness model\b",
        r"\bp/?e\b",
        r"\bintrinsic\b",
        r"\bpromoter\b",
        r"\bshareholding\b",
        r"\bbrand\b",
    ),
    "risk": (
        # Risk may reference domains lightly, but not own valuation verdicts / tape calls
        r"\bbuy the dip\b",
        r"\boverweight\b",
        r"\bunderweight\b",
    ),
    "management": (
        r"\bp/?e\b",
        r"\bintrinsic\b",
        r"\bmargin of safety\b",
        r"\bmomentum\b",
        r"\b52[- ]?week\b",
        r"\binflation\b",
        r"\bgdp\b",
    ),
    "ownership": (
        r"\bmoat\b",
        r"\bbusiness model\b",
        r"\bp/?e\b",
        r"\bintrinsic\b",
        r"\bmargin of safety\b",
        r"\binflation\b",
        r"\bnim\b",
        r"\broe\b",
    ),
}

MANDATES: dict[str, dict[str, Any]] = {
    "business": {
        "role": "business",
        "analyst": "Business Analyst",
        "mandate": (
            "Evaluate whether the company possesses durable competitive advantages "
            "and a high-quality business model."
        ),
        "primary_question": "Is this a business we would like to own?",
        "primary_inputs": [
            "Company Analysis",
            "Company Dossier",
            "Academy",
            "Annual Reports",
        ],
        "outputs": [
            "Business Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "valuation multiples",
            "price attractiveness",
            "macro verdicts",
            "tape / technical calls",
        ],
    },
    "financial": {
        "role": "financial",
        "analyst": "Financial Analyst",
        "mandate": (
            "Determine whether reported financial performance represents durable economic "
            "value creation through earnings quality, cash conversion, returns and balance-sheet resilience."
        ),
        "primary_question": "Do the financial statements support the investment thesis?",
        "primary_inputs": [
            "Financial Intelligence",
            "Company Dossier financial history",
            "Data Validation",
            "Market financial enrichment",
        ],
        "outputs": [
            "Financial Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "brand / moat commentary",
            "valuation attractiveness",
            "macro policy outlook",
        ],
    },
    "valuation": {
        "role": "valuation",
        "analyst": "Valuation Analyst",
        "mandate": (
            "Determine whether the current market price is justified by expected future cash flows, "
            "growth, profitability and risk — focusing on expectations, intrinsic value and margin of safety."
        ),
        "primary_question": (
            "Does today's valuation appropriately reflect the company's long-term intrinsic value "
            "and future expectations?"
        ),
        "primary_inputs": [
            "Valuation research",
            "Financial Intelligence",
            "Market financial enrichment",
            "Data Validation",
        ],
        "outputs": [
            "Valuation Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "business-model storytelling",
            "management character judgements",
            "technical momentum calls",
        ],
    },
    "market": {
        "role": "market",
        "analyst": "Market Analyst",
        "mandate": (
            "Describe what price, volume, liquidity and positioning are signalling — "
            "as a timing overlay, not as fundamental fair value."
        ),
        "primary_question": "What is the market saying?",
        "primary_inputs": [
            "Market tape",
            "Company Dossier market data",
            "Live market evidence",
        ],
        "outputs": [
            "Market Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "franchise quality verdicts",
            "intrinsic value estimates",
            "governance scores",
        ],
    },
    "sector": {
        "role": "sector",
        "analyst": "Sector Analyst",
        "mandate": (
            "Determine whether industry structure, growth, regulation and competitive "
            "intensity create an attractive opportunity set."
        ),
        "primary_question": "Is the industry attractive?",
        "primary_inputs": [
            "Sector Intelligence",
            "Knowledge Foundation",
            "Academy",
            "Broker / industry research",
        ],
        "outputs": [
            "Sector Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "single-name valuation calls",
            "ownership structure commentary",
            "short-term tape calls",
        ],
    },
    "macro": {
        "role": "macro",
        "analyst": "Macro Analyst",
        "mandate": (
            "Assess whether rates, inflation, growth, liquidity and currency help or hurt "
            "the investment case through clear transmission channels."
        ),
        "primary_question": "Does macro help or hurt?",
        "primary_inputs": [
            "Institutional macro briefing",
            "Policy and rates research",
            "External macro series",
        ],
        "outputs": [
            "Macro Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "company moat analysis",
            "shareholding trends",
            "stock-level multiples",
        ],
    },
    "risk": {
        "role": "risk",
        "analyst": "Risk Analyst",
        "mandate": (
            "Identify what can go wrong across business, financial, macro, execution and "
            "valuation channels, with monitoring priorities."
        ),
        "primary_question": "What can go wrong?",
        "primary_inputs": [
            "Company Monitor",
            "Risk models",
            "Company Analysis",
        ],
        "outputs": [
            "Risk Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "buy/sell instructions",
            "ownership recommendations",
        ],
    },
    "management": {
        "role": "management",
        "analyst": "Management Analyst",
        "mandate": (
            "Judge whether governance, capital allocation, execution and communication "
            "justify trust in management."
        ),
        "primary_question": "Can management be trusted?",
        "primary_inputs": [
            "Annual Reports",
            "Conference Calls",
            "Investor Presentations",
            "Company Dossier",
        ],
        "outputs": [
            "Management Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "valuation attractiveness",
            "macro stance",
            "short-term tape commentary",
        ],
    },
    "ownership": {
        "role": "ownership",
        "analyst": "Ownership Analyst",
        "mandate": (
            "Map who owns the business and whether promoter, institutional and insider "
            "trends signal alignment or risk."
        ),
        "primary_question": "Who owns this business?",
        "primary_inputs": [
            "Shareholding disclosures",
            "Company Dossier ownership",
            "Market ownership enrichment",
        ],
        "outputs": [
            "Ownership Opinion",
            "Supporting Evidence",
            "Confidence",
            "Unresolved Questions",
        ],
        "never": [
            "business-model quality scores",
            "earnings trajectory narratives",
            "fair-value estimates",
        ],
    },
}


def mandate_for(role: str) -> dict[str, Any]:
    base = MANDATES.get(role)
    if not base:
        return {
            "role": role,
            "analyst": role.replace("_", " ").title(),
            "mandate": role,
            "primary_question": role,
            "primary_inputs": [],
            "outputs": ["Opinion", "Supporting Evidence", "Confidence", "Unresolved Questions"],
            "never": [],
        }
    return dict(base)
