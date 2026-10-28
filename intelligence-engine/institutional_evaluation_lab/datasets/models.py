"""Benchmark question object — every question carries measurable expectations."""

from __future__ import annotations

from typing import Any


def question(
    question_id: str,
    *,
    text: str,
    category: str,
    intent: list[str] | str,
    frameworks: list[str] | None = None,
    expected_evidence: list[str] | None = None,
    expected_playbook: list[str] | None = None,
    expected_confidence: list[str] | None = None,
    expected_reasoning: list[str] | None = None,
    ground_truth: list[str] | None = None,
    acceptable_alternatives: list[str] | None = None,
    difficulty: str = "medium",
    sector: str | None = None,
    ticker_hint: str | None = None,
    as_of: str | None = None,
    concept_mode: bool | None = None,
    must_not: list[str] | None = None,
    tags: list[str] | None = None,
    answer_format: str | None = None,
    suite: str = "institutional",
    version: str = "iel-v1",
) -> dict[str, Any]:
    intents = [intent] if isinstance(intent, str) else list(intent or [])
    return {
        "question_id": question_id,
        "question": text,
        "intent": intents,
        "framework": list(frameworks or []),
        "expected_evidence": list(expected_evidence or []),
        "expected_playbook": list(expected_playbook or []),
        "expected_confidence": list(expected_confidence or ["low", "medium", "moderate", "high"]),
        "expected_reasoning": list(expected_reasoning or []),
        "ground_truth": list(ground_truth or []),
        "acceptable_alternatives": list(acceptable_alternatives or []),
        "difficulty": difficulty,
        "sector": sector,
        "category": category,
        "ticker_hint": ticker_hint,
        "as_of": as_of,
        "concept_mode": concept_mode,
        "must_not": list(must_not or []),
        "tags": list(tags or []),
        "answer_format": answer_format,
        "suite": suite,
        "version": version,
        "fabricated": False,
    }
