"""Clarification engine — intelligent follow-up questions."""

from __future__ import annotations

from typing import Any


def build_clarifications(
    *,
    question: str,
    ambiguity: dict[str, Any],
    question_status: dict[str, Any],
    entity_status: dict[str, Any],
) -> dict[str, Any]:
    clarifications: list[dict[str, Any]] = []
    flags = set(ambiguity.get("flags") or [])
    q = question or ""

    if "ambiguous_entity" in flags or entity_status.get("needs_clarification"):
        matches = entity_status.get("possible_matches") or ambiguity.get("possible_matches") or []
        names = []
        for m in matches:
            if isinstance(m, dict):
                names.append(str(m.get("name") or m.get("canonical_name") or m.get("ticker") or ""))
            else:
                names.append(str(m))
        names = [n for n in names if n]
        prompt = "Which company do you mean?"
        if names:
            prompt = f"Which company do you mean? Possible matches: {', '.join(names[:6])}."
        clarifications.append(
            {
                "type": "entity_disambiguation",
                "prompt": prompt,
                "options": names[:8],
            }
        )

    if "missing_comparison_target" in flags:
        clarifications.append(
            {
                "type": "comparison_target",
                "prompt": f"Compare with which company? (from: {q})",
                "options": [],
            }
        )

    if "missing_portfolio_context" in flags:
        clarifications.append(
            {
                "type": "portfolio_inputs",
                "prompt": "Please provide capital, time horizon, and risk tolerance for the portfolio.",
                "options": ["Capital", "Time horizon", "Risk tolerance"],
            }
        )

    if "incomplete" in flags or "missing_intent" in flags:
        clarifications.append(
            {
                "type": "question_completion",
                "prompt": "Please restate the research question with the company/topic and the decision you need.",
                "options": [],
            }
        )

    if "too_many_entities" in flags and not clarifications:
        clarifications.append(
            {
                "type": "entity_disambiguation",
                "prompt": "That name matches multiple entities. Which specific company should AGIB research?",
                "options": [str(m.get("name") if isinstance(m, dict) else m) for m in (entity_status.get("possible_matches") or [])][:8],
            }
        )

    if "multiple_questions" in flags:
        clarifications.append(
            {
                "type": "single_question",
                "prompt": "Please ask one institutional research question at a time.",
                "options": [],
            }
        )

    if "contradictory" in flags:
        clarifications.append(
            {
                "type": "resolve_contradiction",
                "prompt": "The question contains contradictory intents. Do you want a buy case, sell case, or balanced assessment?",
                "options": ["Buy case", "Sell case", "Balanced assessment"],
            }
        )

    return {
        "required": bool(clarifications),
        "clarifications": clarifications,
        "count": len(clarifications),
    }
