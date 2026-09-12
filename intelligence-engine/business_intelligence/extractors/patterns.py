"""Compiled regex patterns for official-disclosure evidence extraction."""

from __future__ import annotations

import re

from business_intelligence.schema import (
    CAT_ACQUISITION,
    CAT_BUYBACKS,
    CAT_BUSINESS_DESCRIPTION,
    CAT_CAPACITY,
    CAT_CAPEX,
    CAT_CASH_DEPLOYMENT,
    CAT_COST_OPTIMISATION,
    CAT_CUSTOMERS,
    CAT_DEBT_REDUCTION,
    CAT_DIGITAL,
    CAT_DISTRIBUTION,
    CAT_DIVESTITURE,
    CAT_DIVIDENDS,
    CAT_EXPANSION,
    CAT_GEOGRAPHY,
    CAT_GOVERNANCE,
    CAT_GROWTH_STRATEGY,
    CAT_GUIDANCE_CAPEX,
    CAT_GUIDANCE_COST,
    CAT_GUIDANCE_DEMAND,
    CAT_GUIDANCE_INDUSTRY,
    CAT_GUIDANCE_MARGIN,
    CAT_GUIDANCE_REVENUE,
    CAT_INVESTMENT_PRIORITIES,
    CAT_LIQUIDITY,
    CAT_OPERATING_MODEL,
    CAT_OPPORTUNITY,
    CAT_PRODUCT_LAUNCH,
    CAT_PRODUCTS,
    CAT_REVENUE_MODEL,
    CAT_RISK,
    CAT_SEGMENT_ANALYSIS,
    CAT_SEGMENTS,
    CAT_SERVICES,
    CAT_SUPPLY_CHAIN,
)

# (pattern, category, statement_template_or_callable, fkb_hints)
# statement uses {m} for match group 0 or group 1 when present

PatternRule = tuple[re.Pattern[str], str, str, tuple[str, ...]]


def _r(pat: str, category: str, statement: str, *hints: str) -> PatternRule:
    return (re.compile(pat, re.I), category, statement, hints)


PROFILE_RULES: list[PatternRule] = [
    _r(
        r"(?:is|are)\s+(?:a|an|the)\s+([^.]+?(?:company|provider|manufacturer|platform|services?\s+firm)[^.]*\.)",
        CAT_BUSINESS_DESCRIPTION,
        "Business description disclosed",
    ),
    _r(
        r"business\s+(?:overview|description|model)[:\s]+([^.]+)",
        CAT_BUSINESS_DESCRIPTION,
        "Business overview disclosed",
    ),
    _r(
        r"(?:products?(?:\s+and\s+services)?|portfolio)\s+(?:include|comprises?|covers?)\s+([^.]+)",
        CAT_PRODUCTS,
        "Products disclosed",
    ),
    _r(
        r"(?:offers?|provides?|delivers?)\s+([^.]+?(?:services?|solutions?)[^.]*\.)",
        CAT_SERVICES,
        "Services disclosed",
    ),
    _r(
        r"operating\s+model[:\s]+([^.]+)",
        CAT_OPERATING_MODEL,
        "Operating model disclosed",
    ),
    _r(
        r"revenue\s+model[:\s]+([^.]+)",
        CAT_REVENUE_MODEL,
        "Revenue model disclosed",
        "recurring revenue",
    ),
    _r(
        r"(?:subscription|recurring)\s+revenue",
        CAT_REVENUE_MODEL,
        "Recurring / subscription revenue referenced",
        "recurring revenue",
    ),
    _r(
        r"(?:geographic|geographies|regions?|markets?)\s+(?:include|span|cover|exposure)[:\s]+([^.]+)",
        CAT_GEOGRAPHY,
        "Geographic exposure disclosed",
    ),
    _r(
        r"(?:north america|europe|asia pacific|india|emea|latam|japan|china)",
        CAT_GEOGRAPHY,
        "Geographic market referenced",
    ),
    _r(
        r"(?:customers?|clients?)\s+(?:include|comprise|profile|concentration)[:\s]+([^.]+)",
        CAT_CUSTOMERS,
        "Customer profile disclosed",
    ),
    _r(
        r"client concentration",
        CAT_CUSTOMERS,
        "Client concentration disclosed",
    ),
    _r(
        r"distribution\s+channels?[:\s]+([^.]+)",
        CAT_DISTRIBUTION,
        "Distribution channels disclosed",
    ),
    _r(
        r"supply\s+chain[^.]*",
        CAT_SUPPLY_CHAIN,
        "Supply chain reference disclosed",
    ),
]

SEGMENT_RULES: list[PatternRule] = [
    _r(
        r"(?:business|operating)\s+segments?[:\s]+([^.]+)",
        CAT_SEGMENTS,
        "Operating segments disclosed",
    ),
    _r(
        r"(?:verticals?|segments?)\s+(?:include|remained|were|are)\s+([^.]+)",
        CAT_SEGMENTS,
        "Segment list disclosed",
    ),
    _r(
        r"revenue\s+by\s+segment[^.]*",
        CAT_SEGMENT_ANALYSIS,
        "Revenue by segment disclosed",
    ),
    _r(
        r"(?:profit|margin)\s+by\s+segment[^.]*",
        CAT_SEGMENT_ANALYSIS,
        "Profit by segment disclosed",
    ),
    _r(
        r"capital\s+allocation\s+by\s+segment[^.]*",
        CAT_SEGMENT_ANALYSIS,
        "Capital allocation by segment disclosed",
        "capital allocation",
    ),
    _r(
        r"(?:industry\s+vertical|service.?line)\s+contribution[^.]*",
        CAT_SEGMENT_ANALYSIS,
        "Segment contribution disclosed",
    ),
    _r(
        r"\b(BFSI|Financial Services|Retail|Communications|Manufacturing|Hi-Tech|Energy & Utilities|Healthcare)\b",
        CAT_SEGMENTS,
        "Segment / vertical named: {m}",
    ),
]

STRATEGY_RULES: list[PatternRule] = [
    _r(
        r"growth\s+strategy[^.]*",
        CAT_GROWTH_STRATEGY,
        "Growth strategy disclosed",
        "organic growth",
    ),
    _r(
        r"expand(?:ing)?\s+(?:the\s+)?export[^.]*",
        CAT_GROWTH_STRATEGY,
        "Expand export business",
        "organic growth",
    ),
    _r(
        r"(?:long.?term\s+)?strategy\s+(?:emphasises|emphasizes|includes|focus(?:es)?\s+on)[:\s]+([^.]+)",
        CAT_GROWTH_STRATEGY,
        "Strategy priorities disclosed",
    ),
    _r(
        r"priority\s+themes?\s+include\s+([^.]+)",
        CAT_GROWTH_STRATEGY,
        "Priority themes disclosed",
    ),
    _r(
        r"expansion\s+plans?[^.]*",
        CAT_EXPANSION,
        "Expansion plans disclosed",
    ),
    _r(
        r"cost\s+(?:optimisation|optimization|efficiency|discipline)[^.]*",
        CAT_COST_OPTIMISATION,
        "Cost optimisation disclosed",
        "margin",
    ),
    _r(
        r"(?:digital|cloud|AI|generative AI|automation)\s+(?:initiatives?|capabilities|platforms?|transformation|services?)[^.]*",
        CAT_DIGITAL,
        "Digital initiative disclosed",
    ),
    _r(
        r"capacity\s+expansion[^.]*",
        CAT_CAPACITY,
        "Capacity expansion disclosed",
    ),
    _r(
        r"product\s+launch(?:es)?[^.]*",
        CAT_PRODUCT_LAUNCH,
        "Product launch disclosed",
    ),
    _r(
        r"acquisition[s]?[^.]*",
        CAT_ACQUISITION,
        "Acquisition commentary disclosed",
        "capital allocation",
    ),
    _r(
        r"divestiture[s]?|divestment[s]?[^.]*",
        CAT_DIVESTITURE,
        "Divestiture commentary disclosed",
        "capital allocation",
    ),
    _r(
        r"(?:capital\s+expenditure|capex)\s+(?:plan|programme|program|guidance)?[^.]*",
        CAT_CAPEX,
        "Capex commentary disclosed",
        "capital allocation",
    ),
    _r(
        r"debt\s+(?:reduction|repayment|deleverag)[^.]*",
        CAT_DEBT_REDUCTION,
        "Debt reduction disclosed",
        "debt reduction",
    ),
]

CAPITAL_RULES: list[PatternRule] = [
    _r(
        r"dividend(?:s)?(?:\s+policy)?[^.]*",
        CAT_DIVIDENDS,
        "Dividend commentary disclosed",
        "capital allocation",
    ),
    _r(
        r"buyback[s]?|share\s+repurchase[s]?[^.]*",
        CAT_BUYBACKS,
        "Buyback commentary disclosed",
        "capital allocation",
    ),
    _r(
        r"(?:capital\s+return|shareholder\s+returns?)[^.]*",
        CAT_CASH_DEPLOYMENT,
        "Shareholder returns / capital return disclosed",
        "capital allocation",
    ),
    _r(
        r"liquidity[^.]*",
        CAT_LIQUIDITY,
        "Liquidity commentary disclosed",
        "liquidity",
    ),
    _r(
        r"cash\s+deployment[^.]*",
        CAT_CASH_DEPLOYMENT,
        "Cash deployment disclosed",
        "cash deployment",
    ),
    _r(
        r"investment\s+priorit(?:y|ies)[^.]*",
        CAT_INVESTMENT_PRIORITIES,
        "Investment priorities disclosed",
        "capital allocation",
    ),
    _r(
        r"continued\s+investment\s+in\s+([^.]+)",
        CAT_INVESTMENT_PRIORITIES,
        "Continued investment disclosed",
        "capital allocation",
    ),
    _r(
        r"capital\s+allocation[^.]*",
        CAT_CASH_DEPLOYMENT,
        "Capital allocation commentary disclosed",
        "capital allocation",
    ),
]

RISK_THEMES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"commodity\s+price", re.I), "Commodity prices"),
    (re.compile(r"currency|forex|fx\s+movement|foreign\s+exchange", re.I), "Currency"),
    (re.compile(r"interest\s+rate", re.I), "Interest rates"),
    (re.compile(r"competition|competitive\s+pressure", re.I), "Competition"),
    (re.compile(r"regulat(?:ion|ory)", re.I), "Regulation"),
    (re.compile(r"technolog(?:y|ical)\s+disruption", re.I), "Technology disruption"),
    (re.compile(r"(?:project\s+)?execution\s+risk", re.I), "Execution"),
    (re.compile(r"supply\s+chain", re.I), "Supply chain"),
    (re.compile(r"client\s+concentration|customer\s+concentration", re.I), "Customer concentration"),
    (re.compile(r"climate", re.I), "Climate"),
    (re.compile(r"cyber(?:\s|-)?(?:security|threats?)", re.I), "Cybersecurity"),
    (re.compile(r"talent\s+availability|wage\s+inflation", re.I), "Talent / wage inflation"),
    (re.compile(r"geopolitic", re.I), "Geopolitical"),
    (re.compile(r"reputational", re.I), "Reputational"),
]

OPPORTUNITY_RULES: list[PatternRule] = [
    _r(
        r"growth\s+opportunit(?:y|ies)[^.]*",
        CAT_OPPORTUNITY,
        "Growth opportunity disclosed",
        "organic growth",
    ),
    _r(
        r"(?:industry|market)\s+expansion[^.]*",
        CAT_OPPORTUNITY,
        "Industry / market expansion disclosed",
    ),
    _r(
        r"new\s+products?[^.]*",
        CAT_OPPORTUNITY,
        "New products opportunity disclosed",
    ),
    _r(
        r"export\s+opportunit(?:y|ies)[^.]*",
        CAT_OPPORTUNITY,
        "Export opportunity disclosed",
    ),
    _r(
        r"margin\s+improvement[^.]*",
        CAT_OPPORTUNITY,
        "Margin improvement initiative disclosed",
        "margin",
    ),
    _r(
        r"capacity\s+utilisation|capacity\s+utilization[^.]*",
        CAT_OPPORTUNITY,
        "Capacity utilisation disclosed",
    ),
    _r(
        r"efficiency\s+program(?:me)?s?[^.]*",
        CAT_OPPORTUNITY,
        "Efficiency programme disclosed",
        "margin",
    ),
    _r(
        r"large\s+deal\s+wins?[^.]*",
        CAT_OPPORTUNITY,
        "Large deal wins disclosed",
        "organic growth",
    ),
]

GUIDANCE_RULES: list[PatternRule] = [
    _r(
        r"(?:revenue|growth)\s+guidance[^.]*",
        CAT_GUIDANCE_REVENUE,
        "Revenue / growth guidance disclosed",
    ),
    _r(
        r"maintaining\s+(?:our\s+)?(?:previously\s+communicated\s+)?[^.]*guidance[^.]*",
        CAT_GUIDANCE_REVENUE,
        "Guidance maintained as stated",
    ),
    _r(
        r"margin\s+guidance[^.]*",
        CAT_GUIDANCE_MARGIN,
        "Margin guidance disclosed",
        "margin",
    ),
    _r(
        r"margin\s+commentary[^.]*",
        CAT_GUIDANCE_MARGIN,
        "Margin commentary disclosed",
        "margin",
    ),
    _r(
        r"capex\s+guidance[^.]*",
        CAT_GUIDANCE_CAPEX,
        "Capex guidance disclosed",
        "capital allocation",
    ),
    _r(
        r"demand\s+(?:environment|outlook)[^.]*",
        CAT_GUIDANCE_DEMAND,
        "Demand outlook disclosed",
    ),
    _r(
        r"industry\s+outlook[^.]*",
        CAT_GUIDANCE_INDUSTRY,
        "Industry outlook disclosed",
    ),
    _r(
        r"cost\s+outlook[^.]*",
        CAT_GUIDANCE_COST,
        "Cost outlook disclosed",
    ),
    _r(
        r"without\s+providing\s+numerical\s+forward\s+guidance[^.]*",
        CAT_GUIDANCE_DEMAND,
        "No numerical forward guidance stated in extract",
    ),
]

GOVERNANCE_RULES: list[PatternRule] = [
    _r(
        r"board\s+(?:composition|changes?|appointment|resignation)[^.]*",
        CAT_GOVERNANCE,
        "Board commentary disclosed",
    ),
    _r(
        r"auditor\s+(?:changes?|appointment|resignation|rotation)[^.]*",
        CAT_GOVERNANCE,
        "Auditor change commentary disclosed",
    ),
    _r(
        r"management\s+changes?[^.]*",
        CAT_GOVERNANCE,
        "Management change disclosed",
    ),
    _r(
        r"related[- ]party[^.]*",
        CAT_GOVERNANCE,
        "Related-party commentary disclosed",
    ),
    _r(
        r"(?:committee\s+structures?|independence\s+criteria|whistle.?blower|shareholder\s+grievance)[^.]*",
        CAT_GOVERNANCE,
        "Governance observation disclosed",
    ),
    _r(
        r"board\s+oversight[^.]*",
        CAT_GOVERNANCE,
        "Board oversight disclosed",
    ),
]


def apply_rules(
    text: str,
    rules: list[PatternRule],
) -> list[tuple[str, str, re.Match[str], tuple[str, ...]]]:
    """Return (category, statement, match, hints) for each rule hit (first match per rule)."""
    hits: list[tuple[str, str, re.Match[str], tuple[str, ...]]] = []
    if not text:
        return hits
    for pat, category, statement, hints in rules:
        m = pat.search(text)
        if not m:
            continue
        stmt = statement
        if "{m}" in stmt:
            captured = (m.group(1) if m.lastindex else m.group(0)).strip()
            stmt = stmt.replace("{m}", captured)
        elif m.lastindex and m.group(1):
            # Prefer short structured statement from capture when template is generic
            captured = re.sub(r"\s+", " ", m.group(1).strip())
            if len(captured) <= 160 and captured.lower() not in stmt.lower():
                stmt = f"{statement}: {captured}" if not statement.endswith("disclosed") else f"{statement.rstrip('.')}: {captured}"
        hits.append((category, stmt, m, hints))
    return hits


def extract_risk_themes(text: str) -> list[tuple[str, re.Match[str]]]:
    out: list[tuple[str, re.Match[str]]] = []
    if not text:
        return out
    for pat, label in RISK_THEMES:
        m = pat.search(text)
        if m:
            out.append((label, m))
    return out


def extract_list_items(text: str, lead: re.Pattern[str]) -> list[str]:
    """Split 'X include A, B, and C' style lists into atomic items."""
    m = lead.search(text or "")
    if not m:
        return []
    rest = m.group(1) if m.lastindex else m.group(0)
    rest = rest.split(".")[0]
    parts = re.split(r",|\band\b|;", rest)
    items = [re.sub(r"\s+", " ", p).strip(" .;") for p in parts if p.strip()]
    return [i for i in items if 2 <= len(i) <= 80]
