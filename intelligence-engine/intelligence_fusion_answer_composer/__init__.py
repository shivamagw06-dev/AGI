"""Intelligence Fusion & Answer Composer (IFAC) — Phase 9.1.

Orchestration layer above institutional engines. Does not generate new
intelligence; fuses existing engine outputs into institutional reports.
"""

from __future__ import annotations

from intelligence_fusion_answer_composer.compose import compose, compose_from_provider_results
from intelligence_fusion_answer_composer.production import (
    confidence_board,
    debug_last,
    health,
    provenance_sample,
    routing_table,
    templates_catalog,
)

LAYER = "intelligence_fusion_answer_composer"
VERSION = "1.0"
PROGRAMME = "Phase 9.1 Intelligence Fusion & Answer Composer"

__all__ = [
    "LAYER",
    "VERSION",
    "PROGRAMME",
    "compose",
    "compose_from_provider_results",
    "health",
    "templates_catalog",
    "routing_table",
    "confidence_board",
    "debug_last",
    "provenance_sample",
]
