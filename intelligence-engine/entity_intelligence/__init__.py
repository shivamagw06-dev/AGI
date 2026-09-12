"""Entity Intelligence — verified entity contract before KUL."""

from entity_intelligence.production import analyse, health, soft_slice_for_ask_agi
from entity_intelligence.schema import EI_VERSION, PROGRAMME

__all__ = ["EI_VERSION", "PROGRAMME", "analyse", "health", "soft_slice_for_ask_agi"]
