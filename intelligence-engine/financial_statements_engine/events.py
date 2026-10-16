"""Shared Evidence / Processing Event Bus catalogue (FSE-00…FSE-07)."""

from __future__ import annotations

# Collection (FSE-02)
COLLECTION_EVENTS = (
    "discovery.filing_found",
    "discovery.filing_updated",
    "evidence.stored",
    "evidence.duplicate_skipped",
    "evidence.restatement_candidate",
    "collection.job_failed",
    "collection.job_completed",
)

# Parsing (FSE-04) — legacy aliases retained during migration
PARSE_EVENTS_LEGACY = (
    "parse.started",
    "parse.completed",
    "parse.failed",
    "parse.quarantined",
)

# Parsing quality (FSE-04.1) — versioned (consumers must use these)
PARSE_EVENTS_V1 = (
    "parse.started.v1",
    "parse.completed.v1",
    "parse.failed.v1",
    "parse.quarantined.v1",
    "draft.created.v1",
    "draft.updated.v1",
    "schema.updated.v1",
    "unknown_metric.queued.v1",
    "parser.certified.v1",
    "parser.certification_failed.v1",
)

# Evidence Coverage Matrix (FSE-04.2)
COVERAGE_EVENTS_V1 = (
    "coverage.matrix.created.v1",
    "coverage.history.appended.v1",
    "coverage.regression.detected.v1",
)

# Production Certification Corpus (FSE-04.3)
PCC_EVENTS_V1 = (
    "pcc.certification.started.v1",
    "pcc.certification.completed.v1",
    "pcc.certification.failed.v1",
    "pcc.case.failed.v1",
    "pcc.regression.detected.v1",
)

# Validation & Financial Quality Engine (FSE-05)
VALIDATION_EVENTS_V1 = (
    "validation.started.v1",
    "validation.completed.v1",
    "validation.approved.v1",
    "validation.rejected.v1",
    "validation.quarantined.v1",
)

# Financial Warehouse (FSE-06)
WAREHOUSE_EVENTS_V1 = (
    "warehouse.facts_published.v1",
    "warehouse.publish_rejected.v1",
)

# Derived Metrics Engine (FSE-07)
DERIVED_METRICS_EVENTS_V1 = (
    "derived_metrics.calculated.v1",
    "derived_metrics.published.v1",
    "derived_metrics.calculation_failed.v1",
    "derived_metrics.restatement_recalculated.v1",
)

# Pipeline Orchestrator (FSE-00) — additive coordination events only
ORCHESTRATOR_EVENTS_V1 = (
    "workflow.created.v1",
    "workflow.queued.v1",
    "stage.started.v1",
    "stage.completed.v1",
    "stage.failed.v1",
    "stage.skipped.v1",
    "workflow.completed.v1",
    "workflow.failed.v1",
    "workflow.retrying.v1",
    "workflow.dead_letter.v1",
    "workflow.cancelled.v1",
)

PARSE_EVENTS = PARSE_EVENTS_LEGACY + PARSE_EVENTS_V1 + COVERAGE_EVENTS_V1 + PCC_EVENTS_V1

EVENT_TYPES = (
    COLLECTION_EVENTS
    + PARSE_EVENTS
    + VALIDATION_EVENTS_V1
    + WAREHOUSE_EVENTS_V1
    + DERIVED_METRICS_EVENTS_V1
    + ORCHESTRATOR_EVENTS_V1
)
