"""Editorial scorecard — rate every response for institutional quality."""

from __future__ import annotations

import re
from typing import Any

from editorial_excellence.schema import (
    AVOID_STYLE,
    EDITORIAL_PASS_THRESHOLD,
    EDITORIAL_SCORECARD,
    FORWARD_RATINGS,
    SUCCESS_FORWARD_YES_PCT,
)
from institutional_writing_constitution.schema import FORBIDDEN_PHRASES


def _collect_response_text(pack: dict[str, Any]) -> str:
    parts: list[str] = []
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or pack.get("writing_sections") or {}
    for val in sections.values():
        if isinstance(val, dict):
            parts.append(str(val.get("text") or ""))
            if isinstance(val.get("narrative"), list):
                parts.extend(str(x) for x in val["narrative"])
            parts.extend(str(x) for x in (val.get("bullets") or val.get("observations") or val.get("questions") or val.get("items") or []))
            parts.append(str(val.get("current_evidence_indicates") or ""))
    return " ".join(parts)


def _section(pack: dict[str, Any], *keys: str) -> dict[str, Any]:
    sections = (pack.get("institutional_writing_constitution") or {}).get("sections") or pack.get("writing_sections") or {}
    for k in keys:
        if sections.get(k):
            return sections[k]
    return {}


def _repetitive_evidence(text: str) -> bool:
    return text.lower().count("evidence suggests") >= 3


def _infer_forward_rating(overall: float, problems: list[str]) -> str:
    if overall >= 95 and not problems:
        return "YES"
    if overall >= EDITORIAL_PASS_THRESHOLD and len(problems) <= 1:
        return "MINOR_EDITS"
    if overall >= 70:
        return "MAJOR_EDITS"
    return "REWRITE"


def _forward_score(rating: str) -> float:
    return {"YES": 100.0, "MINOR_EDITS": 85.0, "MAJOR_EDITS": 65.0, "REWRITE": 30.0}.get(rating, 0.0)


def score_editorial(pack: dict[str, Any]) -> dict[str, Any]:
    """Full editorial scorecard for one response pack."""
    text = _collect_response_text(pack)
    lower = text.lower()
    validation = pack.get("writing_constitution_validation") or {}
    forbidden = validation.get("forbidden_hits") or [
        p for p in FORBIDDEN_PHRASES if p in lower
    ]
    avoid_hits = [p for p in AVOID_STYLE if p in lower]

    exec_sec = _section(pack, "executive_summary")
    debate = _section(pack, "investment_debate", "investment_meaning", "what_matters_most")
    evidence = _section(pack, "supporting_evidence", "what_evidence_suggests")
    uncertainty = _section(pack, "key_uncertainties", "what_could_change_view")
    conclusion = _section(pack, "research_conclusion")
    questions = _section(pack, "questions_before_you_decide")

    problems: list[str] = []
    if exec_sec and len(str(exec_sec.get("text") or "").split()) < 20:
        problems.append("executive_summary_too_generic")
    if not debate.get("narrative") and not debate.get("bullets") and not debate.get("text"):
        problems.append("investment_debate_unclear")
    if _repetitive_evidence(text):
        problems.append("evidence_repetitive")
    if len(text.split()) > 800 and "because" not in lower:
        problems.append("too_many_facts")
    if "because" not in lower and "depends on" not in lower:
        problems.append("too_little_explanation")
    if not conclusion.get("largest_uncertainty_remains"):
        problems.append("weak_conclusion")
    if not uncertainty.get("items") and not uncertainty.get("invalidation_scenarios"):
        problems.append("missing_uncertainty")
    if forbidden or avoid_hits:
        problems.append("prohibited_recommendation_language")

    base = 88 if validation.get("passed") else 62
    penalty = min(30, len(problems) * 4 + len(forbidden) * 8)

    scores = {
        "clarity": max(0, min(100, base + 6 - len(problems))),
        "institutional_tone": max(0, 95 - len(forbidden) * 15 - len(avoid_hits) * 5),
        "business_understanding": max(0, min(100, base + (10 if "because" in lower or "make money" in lower or "business" in lower else 0))),
        "investment_insight": max(0, min(100, base + (10 if debate.get("narrative") or debate.get("text") else 0))),
        "evidence_integration": max(0, min(100, base + (10 if evidence.get("assertion_backed") or evidence.get("observations") else 0))),
        "narrative_flow": max(0, min(100, base + (8 if debate.get("narrative") else 0))),
        "explanation_quality": max(0, min(100, base + (8 if "because" in lower or "depends on" in lower else -5))),
        "portfolio_relevance": max(0, min(100, base + (6 if len(questions.get("questions") or []) >= 3 else 0))),
        "investor_usefulness": max(0, min(100, base + 4)),
        "forward_without_editing": 0.0,  # set after overall computed
    }
    overall = round(sum(v for k, v in scores.items() if k != "forward_without_editing") / 9 - penalty * 0.3, 1)
    overall = max(0, min(100, overall))
    scores["overall_editorial_score"] = overall
    scores["forward_without_editing"] = _forward_score(forward := _infer_forward_rating(overall, problems))
    passed = overall >= EDITORIAL_PASS_THRESHOLD and not forbidden

    return {
        "scorecard": scores,
        "dimensions": list(EDITORIAL_SCORECARD),
        "overall_editorial_score": overall,
        "forward_without_editing": forward,
        "forward_test": "Would a portfolio manager forward this response without editing?",
        "success_target_yes_pct": SUCCESS_FORWARD_YES_PCT,
        "passed": passed,
        "writing_problems": problems,
        "forbidden_hits": forbidden,
        "avoid_style_hits": avoid_hits,
    }


def quality_gates(pack: dict[str, Any], editorial: dict[str, Any] | None = None) -> dict[str, Any]:
    """Editorial quality gates — response cannot pass unless criteria met."""
    ed = editorial or score_editorial(pack)
    sections = (pack.get("institutional_writing_constitution") or {}).get("sections") or pack.get("writing_sections") or {}
    section_keys = set(sections.keys())

    has_exec = "executive_summary" in section_keys
    has_debate = bool(section_keys & {"investment_debate", "investment_meaning", "what_matters_most"})
    has_evidence = bool(section_keys & {"supporting_evidence", "what_evidence_suggests"})
    has_uncertainty = bool(section_keys & {"key_uncertainties", "what_could_change_view"})
    has_conclusion = "research_conclusion" in section_keys
    has_questions = "questions_before_you_decide" in section_keys

    checks = {
        "executive_summary_exists": has_exec,
        "investment_debate_exists": has_debate,
        "evidence_supports_conclusions": has_evidence,
        "key_uncertainties_explained": has_uncertainty,
        "research_conclusion_complete": has_conclusion,
        "questions_before_you_decide_included": has_questions,
        "no_prohibited_language": len(ed.get("forbidden_hits") or []) == 0,
        "editorial_score_gte_90": ed.get("overall_editorial_score", 0) >= EDITORIAL_PASS_THRESHOLD,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "threshold": EDITORIAL_PASS_THRESHOLD,
    }
