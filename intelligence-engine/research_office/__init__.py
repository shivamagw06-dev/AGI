"""AGIB v2.2 Institutional Research Office — knowledge-only morning research desk."""

from research_office.office.runner import run_after_scheduler_ready, run_morning_desk
from research_office.production import dashboard, health, run
from research_office.schema import PROGRAMME, RO_VERSION

__all__ = [
    "PROGRAMME",
    "RO_VERSION",
    "dashboard",
    "health",
    "run",
    "run_after_scheduler_ready",
    "run_morning_desk",
]
