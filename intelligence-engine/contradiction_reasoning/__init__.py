"""Contradiction Reasoning Soft Layer — step-by-step conflict answers for Ask AGI.

Not a top-level intelligence engine (architecture freeze).
Not Continuous Research Evaluation (app.cre).
"""

from __future__ import annotations

from contradiction_reasoning.detector import is_contradiction_query
from contradiction_reasoning.flags import flags_dict, is_enabled
from contradiction_reasoning.production import health, package_for_ask_agi, quality_gates
from contradiction_reasoning.schema import MODULE_CODE, PROGRAMME, VERSION

__all__ = [
    "MODULE_CODE",
    "PROGRAMME",
    "VERSION",
    "flags_dict",
    "health",
    "is_contradiction_query",
    "is_enabled",
    "package_for_ask_agi",
    "quality_gates",
]
