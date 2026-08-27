"""CIO-01 — Comparative Intelligence Office (cross-company orchestration)."""

from comparative_intelligence.coordinator import ComparisonCoordinator, compare
from comparative_intelligence.schema import CIO01_VERSION, CIO01_WORKSTREAM_ID

__all__ = ["ComparisonCoordinator", "compare", "CIO01_VERSION", "CIO01_WORKSTREAM_ID"]
