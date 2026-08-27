"""AGIB v2.1 Complete Ask Pipeline — soft-wire integration runtime."""

from ask_pipeline.pipeline import run_complete_ask
from ask_pipeline.production import dashboard, health, run
from ask_pipeline.schema import PIPELINE_VERSION, PROGRAMME

__all__ = [
    "PIPELINE_VERSION",
    "PROGRAMME",
    "dashboard",
    "health",
    "run",
    "run_complete_ask",
]
