"""Language analysis — surface cues for intent resolution (deterministic)."""

from __future__ import annotations

import re
from typing import Any


_EXPLAIN = re.compile(
    r"\b(why|explain|how (?:does|do|would|should|can)|what (?:makes|causes)|reason|because)\b",
    re.I,
)
_COMPARE = re.compile(r"\b(compare|comparison|versus|\bvs\.?\b|relative to|difference between|which of)\b", re.I)
_ANALYSE = re.compile(
    r"\b(analyse|analyze|assess|evaluate|investigate|determine whether|how would you|what evidence|"
    r"list at least|construct|identify|which (?:additional )?evidence)\b",
    re.I,
)
_EDUCATION = re.compile(
    r"^(what is|what's|define|meaning of)\b|\bwhat is a\b|\bwhat does .+ mean\b",
    re.I,
)
_VALUATION = re.compile(
    r"\b(valu(?:e|ation)|fair value|dcf|ev/?ebitda|p/?e\b|price[- ]to[- ]book|p/?b\b|"
    r"residual income|sotp|sum[- ]of[- ]the[- ]parts|multiple|overvalued|undervalued|expensive|cheap)\b",
    re.I,
)
# Portfolio / allocation / rebalancing — exclude bare "capital allocation" (company governance).
_PORTFOLIO = re.compile(
    r"\b(should i invest|should we invest|portfolio decision|portfolio review|"
    r"portfolio construction|portfolio risk|portfolio\b|position siz(?:e|ing)|"
    r"rebalanc(?:e|ing|ed)|watchlist|overweight|underweight|pair trade|"
    r"sector allocation|asset allocation|(?<!capital )allocation|"
    r"buy |sell |recommend)\b",
    re.I,
)
_RISK = re.compile(
    r"\b(risk review|risk checklist|risks?|drawdown|downside|volatility|var\b|tail risk)\b",
    re.I,
)
_ACCOUNTING = re.compile(
    r"\b(accounting|cash flow|operating cash|accrual|earnings quality|working capital|"
    r"revenue growth|cash conversion|balance sheet|revenue recognition|npa|"
    r"inventory days|capitali[sz]ed costs?|deferred tax|promoter pledg|"
    r"statements? and notes|notes to accounts|lease capitali)\b",
    re.I,
)
_INDUSTRY = re.compile(
    r"\b(industry|sector|cement|steel|software|fmcg|hospitals?|pharmaceutical|"
    r"it services|psu banks?|value chain|peers?|"
    r"indian (?:airlines?|auto|paints?|metals?|telecom|nbfc|banks?|industrials?|"
    r"utilities|consumer|cement|steel|pharma|fmcg|it services|real estate))\b",
    re.I,
)
_MACRO = re.compile(
    r"\b(macro|inflation|gdp|repo|interest rate|crude|oil prices?|rupee|fx|currency|"
    r"stagflation|transmission)\b",
    re.I,
)
_GOVERNMENT = re.compile(
    r"\b(government|rbi|sebi|gst|budget|pli|import dut(?:y|ies)|policy|regulation|duty)\b",
    re.I,
)
_EVENTS = re.compile(
    r"\b(dividend|buyback|merger|announcement|board meeting|earnings|quarterly results?|"
    r"order wins?|orders?|contracts?|tender|acquisition|guidance)\b",
    re.I,
)
_DOCUMENTS = re.compile(
    r"\b(annual report|investor presentation|transcript|filing|md&a|risk factors?|"
    r"notes to|audited|institutional documents?|document)\b",
    re.I,
)
_REPLAY = re.compile(
    r"\b(replay|point[- ]in[- ]time|as of|available on that date|future (?:information )?leakage|"
    r"before covid|fy\s?\d{2,4}|institutional memory|historical analogues?|"
    r"have we seen this before)\b",
    re.I,
)
_CROSS = re.compile(
    r"\b(simultaneously|cross[- ]domain|using evidence from|macro,? government,? alternative|"
    r"investment committee|evidence package|evidence pack)\b",
    re.I,
)
_PORTFOLIO_STRONG = re.compile(
    r"\b(portfolio decision|portfolio review|portfolio construction|rebalanc(?:e|ing|ed)|"
    r"watchlist|overweight|underweight|pair trade|sector allocation|asset allocation|"
    r"position siz(?:e|ing)|portfolio risk review)\b",
    re.I,
)
_FRAMEWORK_EXPLAIN = re.compile(
    r"\b(when is .+ (?:correct|appropriate|misleading)|correct primary framework|"
    r"when would it be misleading)\b",
    re.I,
)
_INVESTMENT_VIEW = re.compile(
    r"\b(?:your|agi(?:'s|’s)?|our|house) view\b|\bview on\b|\bquick take\b|"
    r"\binvestment (?:view|thesis|case)\b|\b(?:bull|bear|base) case\b|"
    r"\bwhat would change (?:your|the|agi(?:'s|’s)?) view\b|\bcurrent outlook\b",
    re.I,
)


def analyse_language(question: str) -> dict[str, Any]:
    q = str(question or "").strip()
    ql = q.lower()
    # "capital allocation" is company governance — not portfolio allocation intent.
    capital_alloc = bool(re.search(r"\bcapital allocation\b", ql))
    portfolio_hit = bool(_PORTFOLIO.search(ql)) and not (
        capital_alloc and not _PORTFOLIO_STRONG.search(ql) and "portfolio" not in ql
    )
    investment_view = bool(_INVESTMENT_VIEW.search(ql))
    education = bool(_EDUCATION.search(ql)) and not investment_view
    cues = {
        "explain": bool(_EXPLAIN.search(ql)),
        "compare": bool(_COMPARE.search(ql)),
        "analyse": bool(_ANALYSE.search(ql)),
        "education": education,
        "investment_view": investment_view,
        "valuation_lexicon": bool(_VALUATION.search(ql)),
        "portfolio": portfolio_hit,
        "portfolio_strong": bool(_PORTFOLIO_STRONG.search(ql)),
        "risk": bool(_RISK.search(ql)),
        "accounting": bool(_ACCOUNTING.search(ql)),
        "industry": bool(_INDUSTRY.search(ql)),
        "macro": bool(_MACRO.search(ql)),
        "government": bool(_GOVERNMENT.search(ql)),
        "corporate_events": bool(_EVENTS.search(ql)),
        "documents": bool(_DOCUMENTS.search(ql))
        or bool(re.search(r"\b(statements? and notes|notes to accounts)\b", ql)),
        "documents_primary": bool(
            re.search(r"\b(institutional documents?|using .+ documents|annual report)\b", ql)
        ),
        "historical_replay": bool(_REPLAY.search(ql)),
        "cross_domain": bool(_CROSS.search(ql)),
        "framework_explain": bool(_FRAMEWORK_EXPLAIN.search(ql)),
        "why_question": ql.strip().startswith("why") or " why " in f" {ql}",
        "how_would_you": "how would you" in ql or "how should" in ql,
        "list_request": bool(re.search(r"\b(list|enumerate|name every|every evidence)\b", ql)),
        "investment_committee": bool(re.search(r"\binvestment committee\b", ql)),
        "risk_review": bool(re.search(r"\b(risk checklist|risk review|falsify complacency)\b", ql)),
    }
    cue_count = sum(1 for v in cues.values() if v)
    return {
        "question": q,
        "normalized": ql,
        "cues": cues,
        "cue_count": cue_count,
        "word_count": len(ql.split()),
        "fabricated": False,
    }
