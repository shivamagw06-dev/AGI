"""Phase X — AGI Knowledge Unification Layer (KUL).

Deterministic orchestration gateway over every existing institutional
knowledge source. No LLM. No new datasets. Makes stored knowledge
reachable through one planner so Ask no longer siloes CapIQ, memory,
concepts, academy, CGL, and legacy retrieval behind isolated routers.

Core contract:
  question → Query Plan → Knowledge Plan → Providers → Evidence Fusion
           → Company/Concept Intelligence → Coverage Object → Ask
"""

from __future__ import annotations

from knowledge_unification.production import (
    health,
    plan_and_gather,
    soft_slice_for_ask_agi,
)

__all__ = ["health", "plan_and_gather", "soft_slice_for_ask_agi"]

KUL_VERSION = "1.0.0"
PROGRAMME = "Phase X — Knowledge Unification Layer"
