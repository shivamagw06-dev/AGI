"""Classify the question and build an internal reasoning plan (before answering)."""

from __future__ import annotations

import re
from typing import Any

from institutional_reasoning.prompt import (
    ANSWER_STRUCTURE,
    EVIDENCE_PRIORITY,
    EVIDENCE_SOURCE_CATALOG,
    QUESTION_TYPES,
    REASONING_STEPS,
    TOP_RULE,
)

_TICKER = re.compile(r"\b([A-Z]{2,12}(?:BANK)?)\b")
_COMPANY_HINTS = (
    (re.compile(r"\bhdfc\s+bank\b", re.I), "HDFC Bank", "HDFCBANK", "Banking", "India"),
    (re.compile(r"\bicici\s+bank\b", re.I), "ICICI Bank", "ICICIBANK", "Banking", "India"),
    (re.compile(r"\binfosys\b", re.I), "Infosys", "INFY", "IT Services", "India"),
    (re.compile(r"\btata\s+motors\b", re.I), "Tata Motors", "TATAMOTORS", "Automobiles", "India"),
    (re.compile(r"\breliance\b", re.I), "Reliance Industries", "RELIANCE", "Conglomerate", "India"),
)

_TYPE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(contradict|but|despite|whereas|conflict|which\s+signal|interpret)\b", re.I), "Contradiction"),
    (re.compile(r"\b(ipo|draft\s+red\s+herring|listing)\b", re.I), "IPO"),
    (re.compile(r"\b(valuat|p/?e|p/?b|fair\s+value|intrinsic)\b", re.I), "Valuation"),
    (re.compile(r"\b(macro|inflation|gdp|rbi|interest\s+rate|fed)\b", re.I), "Macro"),
    (re.compile(r"\b(sector|industry\s+outlook|peers?\b)", re.I), "Sector"),
    (re.compile(r"\b(compar|vs\.?|versus|against)\b", re.I), "Comparison"),
    (re.compile(r"\b(portfolio|allocation|position\s+size)\b", re.I), "Portfolio"),
    (re.compile(r"\b(what\s+is|explain|define|mean\s+by|concept)\b", re.I), "Education"),
    (re.compile(r"\b(news|headline|announced|today)\b", re.I), "News"),
    (re.compile(r"\b(risk|downside|threat|vulnerability)\b", re.I), "Risk Analysis"),
    (re.compile(r"\b(gdp|elasticity|opportunity\s+cost|fiscal|monetary)\b", re.I), "Economic Concept"),
    (re.compile(r"\b(revenue|profit|margin|cash\s+flow|balance\s+sheet|nim|npa)\b", re.I), "Financial Analysis"),
    (re.compile(r"\b(should\s+i\s+buy|how\s+is|performing|business|company)\b", re.I), "Company Analysis"),
]


def classify_question_type(query: str) -> str:
    text = str(query or "")
    for pattern, qtype in _TYPE_RULES:
        if pattern.search(text):
            return qtype
    return "Company Analysis"


def understand_question(query: str, *, ticker: str | None = None, company: str | None = None) -> dict[str, Any]:
    text = str(query or "").strip()
    company_name = company
    resolved_ticker = (ticker or "").upper() or None
    industry = None
    country = None
    for pattern, name, sym, ind, ctry in _COMPANY_HINTS:
        if pattern.search(text) or (resolved_ticker and resolved_ticker == sym):
            company_name = company_name or name
            resolved_ticker = resolved_ticker or sym
            industry = ind
            country = ctry
            break
    if not resolved_ticker:
        # crude uppercase token fallback — only if looks like equity ticker in query
        m = re.search(r"\b([A-Z]{3,12})\b", text)
        if m and m.group(1) not in {"NIM", "GDP", "IPO", "FCF", "ROE", "EPS", "NPA", "CASA", "WACC"}:
            resolved_ticker = m.group(1)

    qtype = classify_question_type(text)
    intent = _intent_for(qtype, text)
    horizon = None
    hm = re.search(r"\b(short|medium|long)[\s-]?term\b", text, re.I)
    if hm:
        horizon = hm.group(0)

    return {
        "company": company_name,
        "ticker": resolved_ticker,
        "industry": industry,
        "country": country or ("India" if resolved_ticker or company_name else None),
        "intent": intent,
        "time_horizon": horizon,
        "question_type": qtype,
        "question_types_catalog": list(QUESTION_TYPES),
    }


def _intent_for(qtype: str, text: str) -> str:
    if qtype == "Contradiction":
        return "Reconcile conflicting signals with evidence, alternatives, and missing information."
    if re.search(r"\bshould\s+i\s+buy\b", text, re.I):
        return "Current business and financial assessment — not a lecture and not an action instruction."
    if qtype == "Valuation":
        return "Assess current market price relative to business performance using available evidence."
    if qtype == "Education":
        return "Explain the concept in simple English using AGIB Finance Academy knowledge."
    if qtype == "Financial Analysis":
        return "Explain the financial signal and what evidence supports or limits the conclusion."
    return "Provide an evidence-based institutional assessment relevant to the question."


def build_internal_assessment_template(understanding: dict[str, Any]) -> dict[str, Any]:
    """Internal-only structured assessment skeleton (Step 8)."""
    return {
        "overall_assessment": None,
        "business_strength": None,
        "financial_health": None,
        "growth": None,
        "risk": None,
        "confidence": None,
        "key_supporting_evidence": [],
        "missing_evidence": [],
        "known": [],
        "inferred": [],
        "unknown": [],
        "question_type": understanding.get("question_type"),
        "remains_internal": True,
    }


def relevant_analyst_factors(question_type: str) -> list[str]:
    base = ["Business", "Financial Health", "Risk"]
    by_type = {
        "Valuation": ["Valuation", "Growth", "Profitability", "Cash Flow"],
        "Financial Analysis": ["Profitability", "Cash Flow", "Growth", "Financial Health"],
        "Contradiction": ["Cash Flow", "Profitability", "Management", "Financial Health"],
        "Macro": ["Macro", "Industry", "Risk"],
        "Sector": ["Industry", "Competitive Position", "Growth"],
        "Risk Analysis": ["Risk", "Macro", "Financial Health"],
        "IPO": ["Business", "Financial Health", "Valuation", "Risk", "Management"],
        "Company Analysis": ["Business", "Financial Health", "Growth", "Valuation", "Competitive Position", "Management"],
    }
    extra = by_type.get(question_type, ["Growth", "Valuation"])
    seen = set()
    out = []
    for item in base + extra:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_reasoning_plan(
    query: str,
    *,
    ticker: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    understanding = understand_question(query, ticker=ticker, company=company)
    qtype = understanding["question_type"]
    return {
        "enabled": True,
        "top_rule": TOP_RULE,
        "reasoning_steps": list(REASONING_STEPS),
        "question_understanding": understanding,
        "main_question": understanding["intent"],
        "evidence_sources_to_consider": list(EVIDENCE_SOURCE_CATALOG),
        "evidence_priority": dict(EVIDENCE_PRIORITY),
        "validation_checks": [
            "Are multiple providers consistent?",
            "Is data outdated?",
            "Are values conflicting?",
            "Is evidence complete?",
        ],
        "analyst_factors_relevant": relevant_analyst_factors(qtype),
        "contradiction_protocol_required": qtype == "Contradiction",
        "internal_assessment": build_internal_assessment_template(understanding),
        "answer_structure": list(ANSWER_STRUCTURE),
        "communication_rules": [
            "First sentence directly answers the question.",
            "Simple English; explain necessary finance terms.",
            "Never invent facts or change AGIB conclusions.",
            "Never give Buy/Sell/Hold/Accumulate/Avoid or target prices.",
            "Never present inference as fact.",
            "If evidence is missing, state the limitation and reduce confidence.",
        ],
        "final_principle": (
            "Understand first, reason second, communicate last. "
            "Evidence creates conclusions. Conclusions create answers. Never reverse this order."
        ),
        "answer_policy": "evidence_then_reason_then_communicate",
    }
