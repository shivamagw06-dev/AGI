"""FSE-02 collection contracts — jobs, events, targets."""

from __future__ import annotations

from financial_statements_engine.events import EVENT_TYPES as _SHARED_EVENTS

WORKSTREAM_ID = "FSE-02"
SUBSYSTEM = "collection"
VERSION = "fse-02-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "collection_evidence_only_no_buy_sell"

JOB_STATUSES = (
    "queued",
    "discovering",
    "discovered",
    "downloading",
    "downloaded",
    "verifying",
    "verified",
    "stored",
    "event_emitted",
    "completed",
    "failed_transient",
    "failed_permanent",
    "skipped_duplicate",
    "dead_letter",
)

DOCUMENT_TYPES = ("xbrl", "pdf", "html", "xlsx", "zip", "unknown")
PERIOD_TYPES = ("annual", "quarterly", "unknown")
MODES = ("live", "historical")

# Shared allow-list (collection + parse events)
EVENT_TYPES = _SHARED_EVENTS

RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})
NON_RETRYABLE_HTTP = frozenset({400, 401, 403, 404, 410})

MAX_ATTEMPTS = 5
BACKOFF_CAP_S = 60.0
DEFAULT_MIN_INTERVAL_MS = 200
DEFAULT_EVENT_RETENTION_DAYS = 90

SUCCESS_TARGETS = {
    "successful_downloads_pct": 99.0,
    "duplicate_storage_pct_max": 0.1,
    "evidence_traceability_pct": 100.0,
    "restatement_detection_pct": 100.0,
    "raw_evidence_preservation_pct": 100.0,
    "retry_recovery_pct": 95.0,
    "collector_uptime_pct": 99.0,
    "event_emission_after_store_pct": 100.0,
}

HISTORICAL_PRIORITY_ORDER = (
    "latest_annual",
    "latest_quarter",
    "five_year",
    "ten_year",
    "archive",
)
