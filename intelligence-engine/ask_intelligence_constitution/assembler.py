"""Deterministic section assembly — institutional response structure."""

from __future__ import annotations

from typing import Any

from ask_intelligence_constitution.schema import (
    CONFIDENCE_METHODOLOGY,
    INSTITUTIONAL_THINKING_QUESTIONS,
    OUTPUT_SECTIONS,
)


def _txt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("text", "summary", "narrative", "headline", "reason", "title"):
            if value.get(key):
                return _txt(value.get(key))
        return None
    s = str(value).strip()
    return s or None


def _list(value: Any, *, limit: int = 6) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    out: list[str] = []
    for item in value if isinstance(value, (list, tuple)) else [value]:
        t = _txt(item)
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _research_conclusion(
    *,
    company: str,
    stance: str | None,
    uncertainties: list[str],
    questions: list[str],
) -> dict[str, Any]:
    """Research conclusion — never BUY/SELL/TARGET."""
    view = (stance or "Research Priority").strip()
    forbidden = {"Buy", "Sell", "Hold", "Strong Buy", "Accumulate"}
    if view in forbidden:
        view = "Research Priority — further evidence review warranted"

    return {
        "label": "Research Conclusion",
        "summary": (
            f"Current evidence on {company} supports a {view.lower()} stance for institutional research. "
            "This is decision support — not an investment instruction."
        ),
        "business_assessment": "See business_quality section",
        "valuation_assessment": "See valuation section",
        "key_uncertainties": uncertainties[:5],
        "key_questions_remaining": questions[:6],
        "institutional_research_priority": view,
        "user_decides": True,
    }


def _questions_before_you_decide(company: str, ticker: str | None) -> list[str]:
    label = ticker or company
    return [
        f"Is {label}'s valuation attractive relative to its own history and peers?",
        f"Has the investment thesis on {label} changed materially?",
        "What assumptions are already priced into the current valuation?",
        "What evidence would invalidate today's view?",
        f"How does {label} compare with the best alternative use of capital?",
        "Does this fit my portfolio concentration and risk budget?",
    ]


def assemble_sections(
    pack: dict[str, Any],
    *,
    intent: dict[str, Any],
    response_constitution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build constitution v1.0 section map from structured intelligence."""
    rc = response_constitution or {}
    thesis = rc.get("investment_thesis") or {}
    company = rc.get("company") or pack.get("company") or "This company"
    ticker = rc.get("ticker")

    bull = _list((rc.get("bull_vs_bear") or {}).get("bull_case"))
    bear = _list((rc.get("bull_vs_bear") or {}).get("bear_case"))
    why = _list(rc.get("why_agib_thinks_this"))
    supporting = rc.get("supporting_intelligence") or {}

    sections: dict[str, Any] = {
        "executive_summary": _txt(rc.get("direct_answer")) or _txt(pack.get("executive")),
        "investment_context": {
            "primary_intent": intent.get("primary_intent"),
            "real_intent": intent.get("real_intent"),
            "methodology": intent.get("methodology"),
            "required_intelligence": intent.get("required_intelligence"),
        },
        "business_quality": thesis.get("business"),
        "financial_strength": thesis.get("financial_quality"),
        "management": pack.get("management") or "Management assessment pending fuller governance evidence.",
        "growth_outlook": thesis.get("growth"),
        "valuation": thesis.get("valuation"),
        "risks": thesis.get("risks") or "; ".join(_list(supporting.get("risks"))),
        "catalysts": thesis.get("catalysts") or "; ".join(_list(supporting.get("catalysts"))),
        "what_changed": pack.get("what_changed") or "No material thesis delta identified in current evidence pack.",
        "research_conclusion": _research_conclusion(
            company=company,
            stance=_txt(pack.get("house_label")),
            uncertainties=bear or ["Valuation and earnings trajectory remain key uncertainties."],
            questions=_questions_before_you_decide(company, ticker),
        ),
        "questions_before_you_decide": _questions_before_you_decide(company, ticker),
        "supporting_intelligence": supporting,
        "evidence": {
            "items": why,
            "note": "Every evidence item should include source, date, coverage, and confidence when available.",
        },
        "confidence": rc.get("confidence") or {
            "methodology": CONFIDENCE_METHODOLOGY,
            "explanation": pack.get("confidence_explanation"),
        },
        "bull_case": bull,
        "bear_case": bear,
    }
    return {k: sections.get(k) for k in OUTPUT_SECTIONS if k in sections}


def institutional_thinking_framework(
    intent: dict[str, Any],
    *,
    gaps: list[str] | None = None,
) -> dict[str, Any]:
    """Structured answers to internal IC questions — exposed for transparency."""
    answers = {
        INSTITUTIONAL_THINKING_QUESTIONS[0]: intent.get("real_intent"),
        INSTITUTIONAL_THINKING_QUESTIONS[1]: ", ".join(intent.get("required_intelligence") or []),
        INSTITUTIONAL_THINKING_QUESTIONS[2]: ", ".join(intent.get("required_intelligence") or []),
        INSTITUTIONAL_THINKING_QUESTIONS[3]: "; ".join(gaps or []) or "See evidence pack for residual gaps",
        INSTITUTIONAL_THINKING_QUESTIONS[7]: "See questions_before_you_decide section",
    }
    return {
        "questions": list(INSTITUTIONAL_THINKING_QUESTIONS),
        "answers": answers,
        "purpose": (
            "AGI's purpose is not to replace investor judgement. "
            "AGI's purpose is to improve investor judgement. "
            "The final decision always belongs to the investor."
        ),
    }
