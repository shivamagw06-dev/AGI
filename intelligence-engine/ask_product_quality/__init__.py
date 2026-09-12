"""Phase 9.2 — Ask Product Quality & Institutional Answer Excellence (AQE)."""

VERSION = "aqe-v1.0"
PROGRAMME = "Phase 9.2 — Ask Product Quality & Institutional Answer Excellence"

from ask_product_quality.production import dashboard, enrich_answer, health, quality_gate

__all__ = [
    "VERSION",
    "PROGRAMME",
    "dashboard",
    "enrich_answer",
    "health",
    "quality_gate",
]
