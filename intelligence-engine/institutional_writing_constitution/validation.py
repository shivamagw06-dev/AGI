"""Writing quality validation — forbidden language and hierarchy completeness."""

from __future__ import annotations

from typing import Any

from institutional_writing_constitution.schema import (
    EVIDENCE_OBSERVATIONS_MIN,
    EVALUATION_DIMENSIONS,
    EXECUTIVE_SUMMARY_MAX_WORDS,
    FORBIDDEN_PHRASES,
    INSTITUTIONAL_READABILITY_DIMENSIONS,
    QUALITY_TEST_QUESTIONS,
    QUESTIONS_MIN,
)


def _scan_forbidden(text: str) -> list[str]:
    lower = (text or "").lower()
    return [p for p in FORBIDDEN_PHRASES if p in lower]


def _collect_text(pack: dict[str, Any]) -> str:
    parts: list[str] = []
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or {}
    section_order = iwc.get("section_order") or list(sections.keys())
    for key in section_order:
        val = sections.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, dict):
            parts.append(str(val.get("text") or ""))
            parts.append(str(val.get("narrative") or ""))
            parts.extend(str(x) for x in (val.get("bullets") or val.get("observations") or val.get("questions") or val.get("items") or []))
            if isinstance(val.get("narrative"), list):
                parts.extend(str(x) for x in val["narrative"])
            parts.append(str(val.get("current_evidence_indicates") or ""))
    return " ".join(parts)


def _repetitive_evidence_phrasing(text: str) -> bool:
    """Flag if 'Evidence suggests' dominates — v1.1 uses varied templates."""
    lower = text.lower()
    count = lower.count("evidence suggests")
    return count >= 3


def validate_writing_response(pack: dict[str, Any]) -> dict[str, Any]:
    """Validate writing constitution compliance."""
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or {}
    section_order = iwc.get("section_order") or list(sections.keys())
    checks: list[dict[str, Any]] = []

    for key in section_order:
        checks.append({
            "rule": f"section_present:{key}",
            "passed": key in sections and bool(sections[key]),
            "detail": f"{key} present" if sections.get(key) else f"Missing {key}",
        })

    exec_sec = sections.get("executive_summary") or {}
    wc = exec_sec.get("word_count") or 0
    checks.append({
        "rule": "executive_summary_length",
        "passed": wc <= EXECUTIVE_SUMMARY_MAX_WORDS,
        "detail": f"Executive summary {wc}/{EXECUTIVE_SUMMARY_MAX_WORDS} words",
    })

    evidence = sections.get("supporting_evidence") or sections.get("what_evidence_suggests") or {}
    obs = evidence.get("observations") or []
    checks.append({
        "rule": "supporting_evidence_observations",
        "passed": "supporting_evidence" not in sections and "what_evidence_suggests" not in sections
        or len(obs) >= min(EVIDENCE_OBSERVATIONS_MIN, 1),
        "detail": f"{len(obs)} supporting evidence observations",
    })

    debate = sections.get("investment_debate") or {}
    checks.append({
        "rule": "investment_debate_present",
        "passed": "investment_debate" not in section_order or bool(debate.get("narrative") or debate.get("text")),
        "detail": "Investment debate narrative present" if debate else "N/A (template without debate)",
    })

    qsec = sections.get("questions_before_you_decide") or {}
    qs = qsec.get("questions") or pack.get("questions_before_you_decide") or []
    checks.append({
        "rule": "questions_before_you_decide",
        "passed": "questions_before_you_decide" not in section_order or len(qs) >= QUESTIONS_MIN,
        "detail": f"{len(qs)} decision questions",
    })

    full_text = _collect_text(pack)
    forbidden = _scan_forbidden(full_text)
    checks.append({
        "rule": "no_forbidden_language",
        "passed": len(forbidden) == 0,
        "detail": f"Forbidden: {forbidden}" if forbidden else "Institutional tone preserved",
    })

    checks.append({
        "rule": "no_repetitive_evidence_suggests",
        "passed": not _repetitive_evidence_phrasing(full_text),
        "detail": "Varied evidence phrasing" if not _repetitive_evidence_phrasing(full_text) else "Repetitive 'Evidence suggests'",
    })

    rc = sections.get("research_conclusion") or {}
    checks.append({
        "rule": "research_conclusion_not_recommendation",
        "passed": "research_conclusion" not in section_order
        or (rc.get("never_recommends") is True and rc.get("user_decides") is True),
        "detail": "Research conclusion — not investment instruction",
    })

    passed = sum(1 for c in checks if c["passed"])
    return {
        "constitution": "1.1",
        "passed": passed == len(checks),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "forbidden_hits": forbidden,
        "quality_test_questions": list(QUALITY_TEST_QUESTIONS),
        "evaluation_dimensions": list(EVALUATION_DIMENSIONS),
        "institutional_readability_dimensions": list(INSTITUTIONAL_READABILITY_DIMENSIONS),
    }
