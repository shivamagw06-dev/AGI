"""Research Intelligence Hub (RIH) — AGIB v4.0.

Research notes are Intelligence Objects, not static documents.
"""

from research_intelligence_hub.engine import ResearchIntelligenceHubEngine
from research_intelligence_hub.schema import RIH_VERSION, ResearchObject

__all__ = ["RIH_VERSION", "ResearchIntelligenceHubEngine", "ResearchObject"]
