"""Institutional Thesis Construction Engine (ITCE) V1 — RQ2 Sprint 7."""

from __future__ import annotations

from typing import Any

ITCE_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "ITCE"
SPRINT = 7
SPRINT_NAME = "Institutional Thesis Construction Engine (ITCE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.55
MAX_BUILD_MS_TARGET = 60
BENCHMARK_MIN_THESES = 2_000

MIN_SUPPORTING_PILLARS = 4
MIN_MAJOR_CONTRADICTIONS = 2
MIN_CATALYSTS = 3
MIN_THESIS_BREAKING_CONDITIONS = 1

PILLARS: tuple[str, ...] = (
    "Business Quality",
    "Financial Quality",
    "Capital Allocation",
    "Competitive Position",
    "Valuation",
    "Macro Alignment",
    "Portfolio Fit",
)

# Which hypothesis types feed each pillar
PILLAR_SOURCE_TYPES: dict[str, tuple[str, ...]] = {
    "Business Quality": ("Business", "Management"),
    "Financial Quality": ("Financial", "Accounting"),
    "Capital Allocation": ("Capital Allocation", "Management", "Financial"),
    "Competitive Position": ("Competitive", "Industry"),
    "Valuation": ("Valuation", "Forecast"),
    "Macro Alignment": ("Macro", "Industry"),
    "Portfolio Fit": ("Portfolio", "Risk"),
}

# Pillar dependency chain: Business → Financial → Valuation → Portfolio Fit
PILLAR_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "Business Quality": (),
    "Competitive Position": ("Business Quality",),
    "Financial Quality": ("Business Quality",),
    "Capital Allocation": ("Financial Quality",),
    "Macro Alignment": ("Business Quality",),
    "Valuation": ("Financial Quality", "Competitive Position"),
    "Portfolio Fit": ("Valuation", "Macro Alignment"),
}

THESIS_STATES: tuple[str, ...] = (
    "Emerging",
    "Developing",
    "Strong",
    "Very Strong",
    "Weakening",
    "Broken",
    "Rejected",
)

STABILITY_STATES: tuple[str, ...] = (
    "Stable",
    "Improving",
    "Weakening",
    "Volatile",
)

PRESSURE_LEVELS: tuple[str, ...] = ("Low", "Moderate", "High", "Critical")

CATALYST_POLARITIES: tuple[str, ...] = ("Positive", "Negative", "Neutral")

TIMELINE_HORIZONS: tuple[str, ...] = ("Near Term", "Medium Term", "Long Term")

PRIMARY_QUESTION = (
    "What is the strongest institutional investment thesis supported by the evidence?"
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "core_thesis",
    "supporting_pillars",
    "contradictions",
    "catalysts",
    "timeline",
    "confidence",
    "conviction",
    "missing_evidence",
    "status",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "itce-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ITCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Bayesian Belief & Confidence Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "Institutional investors do not invest based on isolated conclusions. "
            "They invest based on a coherent investment thesis supported by interconnected hypotheses."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_build_ms_target": MAX_BUILD_MS_TARGET,
        "pillars": list(PILLARS),
        "pillar_dependencies": {k: list(v) for k, v in PILLAR_DEPENDENCIES.items()},
        "thesis_states": list(THESIS_STATES),
        "stability_states": list(STABILITY_STATES),
        "pressure_levels": list(PRESSURE_LEVELS),
        "catalyst_polarities": list(CATALYST_POLARITIES),
        "timeline_horizons": list(TIMELINE_HORIZONS),
        "quality_rules": {
            "min_supporting_pillars": MIN_SUPPORTING_PILLARS,
            "min_major_contradictions": MIN_MAJOR_CONTRADICTIONS,
            "min_catalysts": MIN_CATALYSTS,
            "min_thesis_breaking_conditions": MIN_THESIS_BREAKING_CONDITIONS,
        },
        "benchmark": {"min_theses": BENCHMARK_MIN_THESES},
        "success_criteria": {
            "thesis_construction": 1.0,
            "logical_consistency": 1.0,
            "pillar_completeness": 1.0,
            "contradiction_handling": 1.0,
            "catalyst_quality": 1.0,
            "conviction_calibration": 1.0,
            "interaction_quantification": 1.0,
            "quality_separation": 1.0,
            "stability_tracking": 1.0,
            "pressure_monitoring": 1.0,
        },
        "world_class_extensions": {
            "pillar_interaction_matrix": True,
            "thesis_stability": True,
            "quality_separate_from_conviction": True,
            "multi_length_narratives": True,
            "thesis_dna": True,
            "conviction_waterfall": True,
            "threshold_monitoring": True,
            "versioned_evolution": True,
            "thesis_pressure_gauge": True,
        },
    }


ITCE_CONSTITUTION: dict[str, Any] = constitution_dict()
