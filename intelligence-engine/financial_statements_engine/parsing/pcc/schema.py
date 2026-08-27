"""FSE-04.3 Production Certification Corpus contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-04.3"
VERSION = "1.0.0"
SUBSYSTEM = "production_certification_corpus"
PROGRAMME = "Financial Statements Engine"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "pcc_never_emits_buy_sell_or_mutates_golden_expected"

# Sector folders (stable keys)
SECTORS: tuple[str, ...] = (
    "banking",
    "nbfc",
    "insurance",
    "information_technology",
    "manufacturing",
    "automobile",
    "pharma",
    "fmcg",
    "telecom",
    "utilities",
    "metals",
    "oil_gas",
    "infrastructure",
    "healthcare",
    "retail",
    "chemicals",
    "logistics",
    "real_estate",
    "mining",
    "conglomerates",
)

# PCC quality gates (production thresholds)
PCC_GATES: dict[str, float] = {
    "parse_manifest_match_pct": 100.0,
    "coverage_matrix_match_pct": 100.0,
    "hierarchy_preservation_pct": 100.0,
    "metric_mapping_accuracy_pct": 99.5,
    "unknown_label_rate_pct_max": 0.5,
    "validation_consistency_pct": 100.0,
    "replay_determinism_pct": 100.0,
    "regression_detection_pct": 100.0,
}

CASE_DIRS = ("raw", "expected", "metadata", "results")
EXPECTED_FILES = (
    "metrics.json",
    "coverage.json",
    "manifest.json",
    "hierarchy.json",
    "unknown_labels.json",
    "validation.json",
    "lineage.json",
    "confidence.json",
)
