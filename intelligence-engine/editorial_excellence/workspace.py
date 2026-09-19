"""Editorial review workspace — internal improvement interface."""

from __future__ import annotations

from typing import Any

from editorial_excellence.scorecard import score_editorial
from editorial_excellence.rules import EDITORIAL_RULES


def _weak_sentences(text: str, problems: list[str]) -> list[str]:
    """Heuristic weak sentence flags for reviewer workspace."""
    weak: list[str] = []
    for sentence in text.replace("\n", " ").split("."):
        s = sentence.strip()
        if not s:
            continue
        lower = s.lower()
        if len(s.split()) > 40:
            weak.append(s[:120] + "…")
        if any(p in lower for p in ("good company", "strong buy", "excellent", "amazing")):
            weak.append(s[:120])
        if problems and "too_little_explanation" in problems and "because" not in lower:
            if len(weak) < 3:
                weak.append(s[:120] + " — lacks explanation")
    return weak[:5]


def _suggested_improvements(problems: list[str], scorecard: dict[str, Any]) -> list[str]:
    suggestions: list[str] = []
    mapping = {
        "executive_summary_too_generic": "Executive Summary: lead with why this matters to a portfolio manager.",
        "investment_debate_unclear": "Add The Investment Debate — what do investors disagree about?",
        "evidence_repetitive": "Vary evidence sentence openings (see Rule ER-021).",
        "too_many_facts": "Cut facts that do not change investment understanding.",
        "too_little_explanation": "Add 'because' and implication language to every major claim.",
        "weak_conclusion": "Research Conclusion must state largest remaining uncertainty.",
        "missing_uncertainty": "Key Uncertainties section required.",
        "prohibited_recommendation_language": "Remove recommendation or hype language.",
    }
    for p in problems:
        if p in mapping:
            suggestions.append(mapping[p])
    if scorecard.get("narrative_flow", 100) < 85:
        suggestions.append("Improve transitions between sections.")
    if scorecard.get("investment_debate_quality", 100) < 85:
        suggestions.append("Sharpen the central investment debate.")
    return suggestions[:6]


def build_review_workspace(pack: dict[str, Any], *, benchmark_id: str | None = None) -> dict[str, Any]:
    """Build internal editorial review record for one response."""
    editorial = score_editorial(pack)
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or pack.get("writing_sections") or {}
    text_parts = []
    for val in sections.values():
        if isinstance(val, dict):
            text_parts.append(str(val.get("text") or ""))
            if isinstance(val.get("narrative"), list):
                text_parts.extend(val["narrative"])
    response_text = " ".join(text_parts)[:4000]

    problems = editorial.get("writing_problems") or []
    scorecard = editorial.get("scorecard") or {}

    return {
        "benchmark_id": benchmark_id,
        "question": pack.get("query") or "",
        "current_response_excerpt": response_text[:1500],
        "editorial_score": editorial.get("overall_editorial_score"),
        "forward_without_editing": editorial.get("forward_without_editing"),
        "scorecard": scorecard,
        "reviewer_notes": "",
        "weak_sentences": _weak_sentences(response_text, problems),
        "writing_problems": problems,
        "suggested_improvements": _suggested_improvements(problems, scorecard),
        "applicable_rules": [r["id"] for r in EDITORIAL_RULES[:8]],
        "previous_versions": [],
        "improved_version": None,
        "internal_only": True,
    }
