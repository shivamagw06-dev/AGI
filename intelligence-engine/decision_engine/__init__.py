"""AGIB Investment Decision Engine — soft-wire multi-layer investment decisions."""

from decision_engine.production import health, package_for_ask_agi, quality_gates
from decision_engine.schema import IDE_VERSION, PROGRAMME

__all__ = ["PROGRAMME", "IDE_VERSION", "health", "package_for_ask_agi", "quality_gates"]

