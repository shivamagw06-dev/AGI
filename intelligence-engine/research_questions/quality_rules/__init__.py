"""Question quality rules — reject generics and enforce institutional minima."""

from __future__ import annotations

import re
from typing import Any

from research_questions.schema import (
    MIN_CONTRADICTION_QUESTIONS,
    MIN_HISTORICAL_QUESTIONS,
    MIN_PEER_QUESTIONS,
    MIN_QUESTIONS_PER_HYPOTHESIS,
    QUALITY_RULES,
)

_GENERIC_PATTERNS = (
    r"^what do we know\b",
    r"^tell me about\b",
    r"^is it good\b",
    r"^is .+ good\??$",
    r"^any risks\??$",
    r"^overview of\b",
    r"^general thoughts\b",
    r"^what is happening\b",
)

_ANSWERABLE_MARKERS = (
    "?",
    "has ",
    "have ",
    "is ",
    "are ",
    "did ",
    "does ",
    "how ",
    "what ",
    "which ",
    "when ",
)

_DECISION_MARKERS = (
    "advantage",
    "narrow",
    "premium",
    "percentile",
    "valuation",
    "casa",
    "funding",
    "margin",
    "growth",
    "peer",
    "historical",
    "priced",
    "risk",
    "eliminate",
    "justify",
    "credit",
    "deposit",
    "roe",
    "roic",
    "multiple",
    "forecast",
    "earnings",
    "competition",
    "resilient",
)


def evaluate_question_quality(
    question: str,
    *,
    required_evidence: list[str] | None = None,
    existing_questions: list[str] | None = None,
) -> dict[str, Any]:
    text = (question or "").strip()
    lower = text.lower()
    evidence = list(required_evidence or [])
    existing = [e.lower().strip() for e in (existing_questions or []) if e]

    specific = len(text) >= 28 and not any(re.search(p, lower) for p in _GENERIC_PATTERNS)
    # Prefer measurable / comparative anchors
    specific = specific and (
        any(
            x in lower
            for x in (
                "ratio",
                "percentile",
                "versus",
                " vs ",
                "above",
                "below",
                "during",
                "last ",
                "peer",
                "historical",
                "cycle",
                "narrow",
                "premium",
                "justify",
                "eliminate",
                "acknowledged",
                "faster",
                "pricing",
                "forward",
                "current",
            )
        )
        or "?" in text
    )

    answerable = any(m in lower for m in _ANSWERABLE_MARKERS) and len(text) <= 220
    evidence_backed = len(evidence) >= 1
    decision_relevant = any(m in lower for m in _DECISION_MARKERS)

    # Non-overlapping: not near-duplicate of an existing question
    non_overlapping = True
    tokens = set(re.findall(r"[a-z0-9]+", lower))
    for prev in existing:
        prev_tokens = set(re.findall(r"[a-z0-9]+", prev))
        if not tokens or not prev_tokens:
            continue
        overlap = len(tokens & prev_tokens) / max(len(tokens | prev_tokens), 1)
        if overlap >= 0.82 or lower == prev:
            non_overlapping = False
            break

    checks = {
        "specific": specific,
        "answerable": answerable,
        "evidence_backed": evidence_backed,
        "decision_relevant": decision_relevant,
        "non_overlapping": non_overlapping,
    }
    passed = all(checks[r] for r in QUALITY_RULES)
    return {
        "rules": checks,
        "passed": passed,
        "failed_rules": [r for r in QUALITY_RULES if not checks[r]],
        "generic_rejected": any(re.search(p, lower) for p in _GENERIC_PATTERNS),
    }


def enforce_quality(
    question_row: dict[str, Any],
    *,
    existing_questions: list[str] | None = None,
) -> dict[str, Any]:
    eval_ = evaluate_question_quality(
        str(question_row.get("question") or ""),
        required_evidence=list(question_row.get("required_evidence") or []),
        existing_questions=existing_questions,
    )
    out = dict(question_row)
    out["quality_rules"] = eval_
    out["quality_compliant"] = bool(eval_["passed"])
    if eval_.get("generic_rejected"):
        out["status"] = "Rejected"
    return out


def coverage_report(questions: list[dict[str, Any]]) -> dict[str, Any]:
    types = [str(q.get("type") or "") for q in questions]
    contradiction = sum(1 for t in types if t == "Contradiction")
    historical = sum(1 for t in types if t == "Historical")
    peer = sum(1 for t in types if t == "Peer")
    texts = [str(q.get("question") or "").strip().lower() for q in questions]
    unique = len(set(texts)) == len(texts)
    compliant = all(q.get("quality_compliant") for q in questions) if questions else False
    return {
        "question_count": len(questions),
        "contradiction_count": contradiction,
        "historical_count": historical,
        "peer_count": peer,
        "unique": unique,
        "quality_compliant": compliant,
        "meets_minima": (
            len(questions) >= MIN_QUESTIONS_PER_HYPOTHESIS
            and contradiction >= MIN_CONTRADICTION_QUESTIONS
            and historical >= MIN_HISTORICAL_QUESTIONS
            and peer >= MIN_PEER_QUESTIONS
            and unique
            and compliant
        ),
        "targets": {
            "min_questions": MIN_QUESTIONS_PER_HYPOTHESIS,
            "min_contradiction": MIN_CONTRADICTION_QUESTIONS,
            "min_historical": MIN_HISTORICAL_QUESTIONS,
            "min_peer": MIN_PEER_QUESTIONS,
        },
    }
