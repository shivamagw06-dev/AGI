"""Load frozen golden answer references by set version."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import GOLDEN_SET_VERSION, GoldenAnswerRef


def load_answers(version: str = GOLDEN_SET_VERSION) -> dict[str, GoldenAnswerRef]:
    if version != "v1":
        raise ValueError(f"Unknown golden set version: {version}")
    from academy.regression.golden_set.v1.answers import answers_by_id

    return answers_by_id()


def answers_as_dicts(version: str = GOLDEN_SET_VERSION) -> list[dict[str, Any]]:
    return [a.to_dict() for a in load_answers(version).values()]
