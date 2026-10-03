"""Intent-gated access to AGI's existing research intelligence stack."""

from .production import (
    SUPPORTED_INTENTS,
    build_research_intelligence_package,
    detect_intent,
)

__all__ = ["SUPPORTED_INTENTS", "build_research_intelligence_package", "detect_intent"]
