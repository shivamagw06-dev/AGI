"""Institutional Research Writer V1 — presentation + writing layer after CIO."""

from research_writer.production import health, package_for_ask_agi, quality_gates
from research_writer.schema import IRW_VERSION, PROGRAMME

__all__ = ["IRW_VERSION", "PROGRAMME", "health", "package_for_ask_agi", "quality_gates"]
