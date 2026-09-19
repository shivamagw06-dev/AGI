"""AGIB Editorial Intelligence Layer — presentation only, never analysis.

AGIB remains the brain. Editorial providers (Gemini today; OpenAI/Claude/Mistral/DeepSeek later)
only rewrite structured intelligence into concise institutional prose.
"""

from __future__ import annotations

from editorial.flags import flags_dict, is_enabled
from editorial.glossary import GLOSSARY, PERMANENT_RULE, plain_english
from editorial.production import health, package_for_ask_agi, quality_gates
from editorial.schema import EDITORIAL_VERSION, PROGRAMME
from editorial.service import (
    EditorialService,
    generateDetailedAnalysis,
    generateQuickAnalysis,
    generateQuickSummary,
    generateRecommendation,
)

__all__ = [
    "EditorialService",
    "GLOSSARY",
    "PERMANENT_RULE",
    "flags_dict",
    "generateDetailedAnalysis",
    "generateQuickAnalysis",
    "generateQuickSummary",
    "generateRecommendation",
    "health",
    "is_enabled",
    "package_for_ask_agi",
    "plain_english",
    "quality_gates",
    "EDITORIAL_VERSION",
    "PROGRAMME",
]
