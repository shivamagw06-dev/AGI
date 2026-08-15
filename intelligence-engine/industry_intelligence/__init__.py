"""Phase 3.1 — Industry Intelligence Engine.

Extends AGI Core v1.0. Does not modify Core modules.
Ask/KUL integration is deferred until Acceptance = 100%.
"""

from industry_intelligence.schema import II_VERSION, PROGRAMME, SPEC, ASK_WIRED, ASK_WIRED_VIA
from industry_intelligence.framework import coverage_report, framework_for

__all__ = ["II_VERSION", "PROGRAMME", "SPEC", "ASK_WIRED", "ASK_WIRED_VIA", "framework_for", "coverage_report"]
