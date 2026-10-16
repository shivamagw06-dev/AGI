"""Blind Red Team runner — engine never receives category labels."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.engine import package_reasoning_answer
from red_team.bank import RED_TEAM_BANK
from red_team.ecr import attach_ecr_to_package
from red_team.rules import RED_TEAM_RULES


def run_blind_item(item: dict[str, Any]) -> dict[str, Any]:
    """Run one Red Team question without disclosing its category to the engine."""
    question = str(item.get("question") or "")
    # Blind call — only the question text.
    packaged = package_reasoning_answer(question)
    packaged = attach_ecr_to_package(packaged)
    return {
        "test_id": item.get("id"),
        # Category kept only on the Red Team side of the result envelope.
        "red_team_category": item.get("category"),
        "question": question,
        "engine_saw_category": False,
        "packaged": packaged,
        "rules": list(RED_TEAM_RULES),
    }


def run_blind_suite(limit: int | None = None) -> list[dict[str, Any]]:
    items = list(RED_TEAM_BANK)
    if limit is not None:
        items = items[:limit]
    return [run_blind_item(item) for item in items]
