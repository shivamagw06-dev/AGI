"""AGIB v3.4 Track A — Intent Resolution Layer (before IERE)."""

from ask_pipeline.intent_resolution.resolver import resolve_intent
from ask_pipeline.intent_resolution.schema import IRL_VERSION, MODULE_CODE, PROGRAMME

__all__ = ["resolve_intent", "IRL_VERSION", "MODULE_CODE", "PROGRAMME"]
