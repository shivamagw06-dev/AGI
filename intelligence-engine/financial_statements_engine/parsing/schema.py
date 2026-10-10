"""FSE-04 Parsing & Normalization Engine — contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-04"
SUBSYSTEM = "parsing"
VERSION = "fse-04-pne-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"
OUTPUT_SCHEMA = "cfdm_statement_draft_v1"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "parsing_drafts_only_no_buy_sell"
WRITES_WAREHOUSE = False
VALIDATES_ACCOUNTING = False
CALCULATES_DERIVED = False

CONFIDENCE_FLAG_THRESHOLD = 0.7

ERROR_CLASSES = (
    "parse_failure",
    "structure_failure",
    "unsupported_format",
    "missing_sections",
    "corrupt_document",
    "encoding_error",
)

QUALITY_TARGETS = {
    "parsing_success_pct": 99.0,
    "deterministic_output_pct": 100.0,
    "unknown_metric_rate_pct_max": 1.0,
    "unit_detection_accuracy_pct": 99.5,
    "currency_detection_accuracy_pct": 100.0,
    "canonical_mapping_accuracy_pct": 99.0,
    "traceability_pct": 100.0,
}

SUPPORTED_FORMATS = ("xbrl", "ixbrl", "pdf", "html", "xlsx", "csv", "json", "xml")
