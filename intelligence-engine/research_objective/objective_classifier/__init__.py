"""Primary + secondary institutional research objective classifier."""

from __future__ import annotations

import re
from typing import Any

from research_objective.schema import PRIMARY_OBJECTIVES, normalize_objective

_BUY = re.compile(
    r"\b(should\s+i\s+buy|buy\s+|worth\s+buying|accumulate|invest\s+in|good\s+buy|"
    r"investment\s+case|investment\s+thesis|should\s+i\s+invest)\b",
    re.I,
)
_SELL = re.compile(r"\b(should\s+i\s+sell|exit|trim|reduce\s+position|book\s+profits?)\b", re.I)
_COMPARE = re.compile(
    r"\b(compare|better\s+than|peer\s+compar)|"
    r"\bvs\.?\b|"
    r"\bversus\b(?!\s+history)",
    re.I,
)
_EDU = re.compile(
    r"\b(explain|what\s+is|what\s+does|define|teach|how\s+does\s+.+\s+work|"
    r"meaning\s+of|tutorial|academy)\b",
    re.I,
)
_MACRO = re.compile(
    r"\b(rbi|fed|federal\s+reserve|imf|rate\s+cut|rate\s+hike|inflation|gdp|"
    r"monetary\s+policy|fiscal|macro|how\s+will\b.+\baffect)\b",
    re.I,
)
_HIST = re.compile(
    r"\b(versus\s+history|vs\s+history|historical|historically|expensive\s+versus|"
    r"cheap\s+versus|percentile|z[- ]?score|mean\s+reversion)\b",
    re.I,
)
_VAL = re.compile(
    r"\b(valuation|pe\b|p/e|pb\b|p/b|ev/ebitda|dcf|fair\s+value|overvalued|"
    r"undervalued|expensive|cheap\s+at)\b",
    re.I,
)
_BIZ = re.compile(
    r"\b(business\s+quality|moat|competitive\s+advantage|franchise|roic|"
    r"capital\s+allocation|operating\s+model)\b",
    re.I,
)
_FIN = re.compile(
    r"\b(financial\s+health|balance\s+sheet|leverage|liquidity|solvency|"
    r"cash\s+flow\s+quality|debt\s+service|credit\s+metrics)\b",
    re.I,
)
_RISK = re.compile(
    r"\b(risk\s+assessment|what\s+are\s+the\s+risks|downside|tail\s+risk|"
    r"stress\s+test|drawdown|volatility\s+risk)\b",
    re.I,
)
_PORT = re.compile(
    r"\b(portfolio|allocation|rebalance|construct|build\s+a\s+.+\s+portfolio|"
    r"position\s+sizing|₹|rs\.?\s*\d|inr\s*\d)\b",
    re.I,
)
_SECTOR = re.compile(
    r"\b(sector\s+attractiveness|is\s+.+\s+sector|sector\s+outlook|"
    r"industry\s+attractiveness|nifty\s+\w+\s+outlook)\b",
    re.I,
)
_INDUSTRY = re.compile(r"\b(industry\s+structure|porter|competitive\s+intensity|value\s+chain)\b", re.I)
_SCENARIO = re.compile(r"\b(scenario|what\s+if|bull\s+case|bear\s+case|base\s+case)\b", re.I)
_FORECAST = re.compile(r"\b(forecast|predict|outlook|next\s+year|fy2[0-9]|guidance)\b", re.I)
_NEWS = re.compile(r"\b(news\s+impact|headline|breaking|market\s+reaction\s+to\s+news)\b", re.I)
_EVENT = re.compile(r"\b(event\s+analysis|earnings\s+event|agm|result\s+day|corporate\s+action)\b", re.I)
_SCREEN = re.compile(r"\b(screen|screener|filter\s+stocks|find\s+stocks|universe)\b", re.I)
_TECH = re.compile(r"\b(technical\s+analysis|chart|rsi|macd|moving\s+average|support|resistance)\b", re.I)
_ACCT = re.compile(r"\b(accounting\s+review|forensic|earnings\s+quality|audit\s+flags?)\b", re.I)
_MGMT = re.compile(r"\b(management\s+assessment|ceo|promoter\s+quality|leadership)\b", re.I)
_OWN = re.compile(r"\b(ownership|promoter\s+holding|fii|dii|shareholding)\b", re.I)
_GOV = re.compile(r"\b(governance|related\s+party|board\s+quality|sebi\s+action)\b", re.I)
_POLICY = re.compile(r"\b(policy\s+analysis|government\s+policy|budget\s+impact)\b", re.I)
_REG = re.compile(r"\b(regulatory|regulation|compliance|rbi\s+guidelines|sebi\s+rules)\b", re.I)

_RULES: list[tuple[re.Pattern[str], str, float]] = [
    # Specific phrases win over broad macro / portfolio / compare cues
    (_EDU, "Educational", 0.97),
    (_HIST, "Historical Analysis", 0.99),
    (_REG, "Regulatory Analysis", 0.97),
    (_POLICY, "Policy Analysis", 0.96),
    (_NEWS, "News Impact", 0.96),
    (_EVENT, "Event Analysis", 0.95),
    (_RISK, "Risk Assessment", 0.97),
    (_COMPARE, "Peer Comparison", 0.98),
    (_SCREEN, "Screening", 0.96),
    (_SCENARIO, "Scenario Analysis", 0.95),
    (_ACCT, "Accounting Review", 0.95),
    (_MGMT, "Management Assessment", 0.95),
    (_OWN, "Ownership Review", 0.94),
    (_GOV, "Governance Review", 0.94),
    (_TECH, "Technical Analysis", 0.95),
    (_INDUSTRY, "Industry Structure", 0.94),
    (_SECTOR, "Sector Attractiveness", 0.94),
    (_PORT, "Portfolio Decision", 0.96),
    (_MACRO, "Macro Impact", 0.97),
    (_BIZ, "Business Quality Assessment", 0.95),
    (_FIN, "Financial Health Assessment", 0.95),
    (_VAL, "Valuation Assessment", 0.95),
    (_FORECAST, "Forecast", 0.93),
    (_SELL, "Investment Evaluation", 0.96),
    (_BUY, "Investment Evaluation", 0.99),
]

_INTENT_TO_OBJECTIVE: dict[str, str] = {
    "Company Research": "Investment Evaluation",
    "Valuation Research": "Valuation Assessment",
    "Financial Analysis": "Financial Health Assessment",
    "Business Quality": "Business Quality Assessment",
    "Risk Analysis": "Risk Assessment",
    "Peer Comparison": "Peer Comparison",
    "Sector Research": "Sector Attractiveness",
    "Macro Research": "Macro Impact",
    "Portfolio Construction": "Portfolio Decision",
    "Portfolio Review": "Portfolio Decision",
    "Educational": "Educational",
    "Academy": "Educational",
    "Forecast": "Forecast",
    "Historical Analysis": "Historical Analysis",
    "Screening": "Screening",
    "Technical Analysis": "Technical Analysis",
    "News Analysis": "News Impact",
    "Event Analysis": "Event Analysis",
    "Scenario Analysis": "Scenario Analysis",
    "Accounting Review": "Accounting Review",
    "Management Assessment": "Management Assessment",
    "Governance Review": "Governance Review",
}


def _secondaries_for(primary: str, text: str) -> list[str]:
    secs: list[str] = []
    checks = [
        (_VAL, "Valuation Assessment"),
        (_RISK, "Risk Assessment"),
        (_FORECAST, "Forecast"),
        (_BIZ, "Business Quality Assessment"),
        (_FIN, "Financial Health Assessment"),
        (_PORT, "Portfolio Decision"),
        (_SECTOR, "Sector Attractiveness"),
        (_MACRO, "Macro Impact"),
        (_HIST, "Historical Analysis"),
        (_COMPARE, "Peer Comparison"),
        (_SCENARIO, "Scenario Analysis"),
    ]
    for pat, obj in checks:
        if obj == primary:
            continue
        if pat.search(text):
            secs.append(obj)
    # Investment Evaluation defaults
    if primary == "Investment Evaluation":
        for obj in (
            "Valuation Assessment",
            "Risk Assessment",
            "Forecast",
            "Business Quality Assessment",
            "Portfolio Decision",
        ):
            if obj not in secs:
                secs.append(obj)
    if primary == "Historical Analysis":
        for obj in ("Valuation Assessment", "Sector Attractiveness"):
            if obj not in secs:
                secs.append(obj)
    if primary == "Macro Impact":
        for obj in ("Forecast", "Sector Attractiveness"):
            if obj not in secs:
                secs.append(obj)
    return secs[:8]


def classify_objective(
    question: str,
    *,
    primary_intent: str | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    text = (question or "").strip()
    if not text:
        return {
            "primary_objective": None,
            "secondary_objectives": [],
            "objective_confidence": 0.0,
            "requires_clarification": True,
            "clarification_reason": "empty_question",
            "candidates": [],
        }

    candidates: list[tuple[str, float]] = []
    for pat, obj, score in _RULES:
        if pat.search(text):
            candidates.append((obj, score))

    primary = None
    conf = 0.0
    if candidates:
        # Prefer first high-confidence rule hit (rules ordered by specificity)
        primary, conf = candidates[0]
        # Boost if multiple rules agree on same objective
        agrees = [c for c in candidates if c[0] == primary]
        if len(agrees) > 1:
            conf = min(0.995, conf + 0.01 * (len(agrees) - 1))
    elif primary_intent:
        mapped = _INTENT_TO_OBJECTIVE.get(primary_intent)
        if mapped:
            primary, conf = mapped, 0.88
        else:
            primary, conf = "Investment Evaluation", 0.72
    else:
        # Weak company-like default
        if entity_type in {"Company", "Equity", "Stock"}:
            primary, conf = "Investment Evaluation", 0.78
        else:
            primary, conf = None, 0.55

    primary = normalize_objective(primary)
    if primary and primary not in PRIMARY_OBJECTIVES:
        primary = None
        conf = 0.5

    secondaries = _secondaries_for(primary or "", text) if primary else []
    # Historical valuation phrasing
    if primary == "Historical Analysis" and _VAL.search(text):
        # keep Historical Analysis as primary (product alias Historical Valuation)
        pass

    requires = conf < 0.85 or primary is None
    return {
        "primary_objective": primary,
        "secondary_objectives": secondaries,
        "objective_confidence": round(conf, 4),
        "requires_clarification": requires,
        "clarification_reason": "low_objective_confidence" if requires else None,
        "candidates": [{"objective": o, "score": s} for o, s in candidates[:6]],
        "objective_alias": (
            "Historical Valuation" if primary == "Historical Analysis" and _VAL.search(text) else None
        ),
    }
