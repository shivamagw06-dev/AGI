"""AGIB v1.2 – Institutional Universe Intelligence (soft registry layer).

Manages any institutional investment universe. Does not reason.
Phases 1–7, Knowledge Factory architecture, and Decision Quality remain frozen.
"""

from __future__ import annotations

from universe_intelligence.production import (
    dashboard,
    health,
    quality_gates_summary,
    run_pipeline,
)
from universe_intelligence.schema import IUI_VERSION, PROGRAMME

__all__ = [
    "IUI_VERSION",
    "PROGRAMME",
    "health",
    "dashboard",
    "run_pipeline",
    "quality_gates_summary",
]
