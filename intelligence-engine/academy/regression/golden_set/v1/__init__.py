"""Frozen golden set v1 — IMMUTABLE. Never edit; create v2 for changes."""

from academy.regression.golden_set.v1.answers import GOLDEN_ANSWERS
from academy.regression.golden_set.v1.companies import BENCHMARK_UNIVERSE, universe_counts
from academy.regression.golden_set.v1.questions import GOLDEN_QUESTIONS

GOLDEN_SET_ID = "golden_set_v1"
IMMUTABLE = True

__all__ = [
    "GOLDEN_SET_ID",
    "IMMUTABLE",
    "GOLDEN_QUESTIONS",
    "GOLDEN_ANSWERS",
    "BENCHMARK_UNIVERSE",
    "universe_counts",
]
