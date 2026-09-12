"""FSE-00 Pipeline Orchestrator contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-00"
VERSION = "1.0.0"
SUBSYSTEM = "pipeline_orchestrator"
PROGRAMME = "Financial Statements Engine"
ORCH_VERSION = "orch-v1.0.0"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "orchestration_only_no_parse_validate_calculate_publish"

# Pipeline stages (strict order)
STAGES = (
    "RAW_EVIDENCE_STORED",
    "PARSE",
    "VALIDATE",
    "WAREHOUSE_PUBLISH",
    "DERIVED_METRICS",
)

# Workflow-level states
WORKFLOW_STATES = (
    "RECEIVED",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "RETRYING",
    "DEAD_LETTER",
    "CANCELLED",
)

# Stage-level statuses
STAGE_STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "SKIPPED",
)

# Deterministic transitions: from → allowed to
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "RECEIVED": ("QUEUED", "CANCELLED"),
    "QUEUED": ("RUNNING", "CANCELLED"),
    "RUNNING": ("COMPLETED", "FAILED", "RETRYING", "DEAD_LETTER", "CANCELLED"),
    "RETRYING": ("QUEUED", "RUNNING", "FAILED", "DEAD_LETTER", "CANCELLED"),
    "FAILED": ("QUEUED", "RETRYING", "DEAD_LETTER", "CANCELLED"),
    "DEAD_LETTER": ("QUEUED", "RETRYING", "CANCELLED"),  # manual replay/retry only
    "COMPLETED": (),  # terminal unless replay creates new attempt record
    "CANCELLED": (),
}

# Orchestration events (additive; never rename existing FSE engine events)
ORCHESTRATOR_EVENTS = (
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

# Retry policy
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 60.0

TRANSIENT_ERROR_CODES = frozenset(
    {
        "TRANSIENT",
        "TIMEOUT",
        "RATE_LIMIT",
        "NETWORK",
        "TEMPORARY",
        "download_failed",
        "503",
        "502",
        "429",
        "408",
    }
)
