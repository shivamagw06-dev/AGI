"""AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation Engine (IHG)."""

from institutional_hypothesis_generation.production import (
    apply_hypothesis_generation,
    configuration,
    dashboard,
    explain,
    generate,
    history,
    rank,
    status,
    telemetry,
)
from institutional_hypothesis_generation.schema import HYPOTHESIS_VERSION, IHG_VERSION

__all__ = [
    "IHG_VERSION",
    "HYPOTHESIS_VERSION",
    "apply_hypothesis_generation",
    "configuration",
    "dashboard",
    "explain",
    "generate",
    "history",
    "rank",
    "status",
    "telemetry",
]
