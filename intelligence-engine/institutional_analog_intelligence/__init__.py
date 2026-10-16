"""AGIB v3.6 Phase 2 Sprint 2.2 — Institutional Memory & Analog Intelligence (IMAI).

Distinct from ILM (`institutional_memory` — learning/mistakes/forecasts).
IMAI answers: "Have we seen this before?"
"""

from institutional_analog_intelligence.production import retrieve
from institutional_analog_intelligence.schema import IMAI_VERSION, MODULE_CODE, PROGRAMME

__all__ = [
    "IMAI_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "retrieve",
]
