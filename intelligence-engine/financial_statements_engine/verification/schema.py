"""FSE-02.2 — End-to-End Production Verification contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-02.2"
SUBSYSTEM = "production_verification"
VERSION = "fse-02.2-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "verification_observability_only_no_buy_sell"

DEFAULT_VERIFY_UNIVERSE = (
    "TCS",
    "RELIANCE",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
)

# Human checklist labels mapped to orchestrator stages
PIPELINE_CHECKLIST = (
    ("raw_evidence_stored", "RAW_EVIDENCE_STORED"),
    ("parse", "PARSE"),
    ("validate", "VALIDATE"),
    ("warehouse_published", "WAREHOUSE_PUBLISH"),
    ("derived_metrics", "DERIVED_METRICS"),
)

SPEC = "docs/FSE_02_2_END_TO_END_PRODUCTION_VERIFICATION.md"
