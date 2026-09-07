"""AGIB Knowledge Factory — Track 1 (v1.0.1 LOCKED soft data layer).

Independent of reasoning engines. Collectors → Validators → Normalizers →
Producers → Validated Knowledge Store → existing Institutional Evidence Producers.

NOT a top-level reasoning engine. Phases 1–7 remain frozen.
"""

from __future__ import annotations

from knowledge_factory.coverage import (
    coverage_dimensions,
    daily_health_scorecard,
    decision_coverage,
    morning_coverage_dashboard,
)
from knowledge_factory.production import (
    coverage_dashboard,
    health,
    historical_depth_coverage,
    quality_gates,
    run_daily_pipeline,
    run_historical_depth_pipeline,
    run_sector_intelligence_pipeline,
    sector_intelligence_coverage,
)

KF_VERSION = "knowledge-factory-v1.0.0"
MODULE_CODE = "KF"
PROGRAMME = "Knowledge Factory (Track 1)"
ARCHITECTURE_STATUS = "SOFT_DATA_LAYER"
NOT_A_TOP_LEVEL_ENGINE = True

__all__ = [
    "KF_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "coverage_dashboard",
    "coverage_dimensions",
    "daily_health_scorecard",
    "decision_coverage",
    "health",
    "historical_depth_coverage",
    "morning_coverage_dashboard",
    "quality_gates",
    "run_daily_pipeline",
    "run_historical_depth_pipeline",
    "run_sector_intelligence_pipeline",
    "sector_intelligence_coverage",
]
