"""FSE-04.1 quality framework contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-04.1"
SUBSYSTEM = "parse_quality"
VERSION = "fse-04.1-quality-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "parser_quality_only_no_buy_sell"

QUALITY_GATES = {
    "metric_extraction_accuracy_pct": 99.5,
    "canonical_mapping_accuracy_pct": 99.5,
    "unknown_metric_rate_pct_max": 0.5,
    "hierarchy_preservation_pct": 100.0,
    "replay_determinism_pct": 100.0,
    "duplicate_draft_rate_pct_max": 0.0,
    "traceability_pct": 100.0,
    "benchmark_pass_rate_pct": 100.0,
}

UNKNOWN_STATUSES = ("open", "approved", "rejected")
