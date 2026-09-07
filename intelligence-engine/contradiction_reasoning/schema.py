"""Contradiction Reasoning — soft reasoning-quality module (not a top-level engine).

Improves Ask AGI answers when facts conflict.
Does not replace AGIB analysis engines.
Not Continuous Research Evaluation (app.cre).
Architecture: v1.0.1 LOCKED — soft-wire only.
"""

from __future__ import annotations

PROGRAMME = "Contradiction Reasoning Soft Layer"
MODULE_CODE = "CXR"
VERSION = "v1.0.0"
ARCHITECTURE_STATUS = "SOFT_WIRE"
NOT_A_TOP_LEVEL_ENGINE = True
NOT_CONTINUOUS_RESEARCH_EVALUATION = True

# Institutional answer structure every contradiction response must follow.
ANSWER_STRUCTURE = (
    "direct_answer",
    "why_this_happened",
    "other_possible_explanations",
    "what_evidence_is_missing",
    "current_conclusion",
)

# Reasoning chain (internal).
REASONING_CHAIN = (
    "facts",
    "do_they_conflict",
    "why_could_they_conflict",
    "possible_explanations",
    "strongest_evidence",
    "missing_evidence",
    "final_answer",
)
