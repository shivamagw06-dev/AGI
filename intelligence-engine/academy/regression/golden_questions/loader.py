"""Load frozen golden questions by set version."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import GOLDEN_SET_VERSION, GoldenQuestion


def load_questions(version: str = GOLDEN_SET_VERSION) -> list[GoldenQuestion]:
    if version != "v1":
        raise ValueError(f"Unknown golden set version: {version} (immutable sets only)")
    from academy.regression.golden_set.v1.questions import GOLDEN_QUESTIONS

    return list(GOLDEN_QUESTIONS)


def questions_as_dicts(version: str = GOLDEN_SET_VERSION) -> list[dict[str, Any]]:
    return [q.to_dict() for q in load_questions(version)]
