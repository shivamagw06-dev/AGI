"""PRP-03 — Observability & Operations constants."""

from __future__ import annotations

PRP_WORKSTREAM_ID = "PRP-03"
PRP_03_ID = PRP_WORKSTREAM_ID
PRP_PRODUCT = "Observability & Operations"
PRP_VERSION = "prp-03-v1.0.0"
PRP_SPEC = "docs/AGI_PRP_03_OBSERVABILITY_OPERATIONS.md"
PRP_ROLE = "production_readiness_observability"
OBS_ENGINE_VERSION = "prp-03-obs-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"

GUIDING_PRINCIPLE = (
    "Observability explains how the platform behaves. "
    "It never changes platform behavior."
)

SEVERITIES = ("debug", "info", "warning", "error", "critical")

HEALTH_STATUSES = ("healthy", "degraded", "unhealthy", "unknown")

MONITORED_SERVICES = (
    "api",
    "security",
    "uag",
    "rw",
    "pub",
    "cci",
    "mpc",
    "performance",
    "knowledge_graph",
    "redis",
    "database",
    "queue",
    "storage",
)

METRIC_NAMES = (
    "request_count",
    "latency_ms",
    "cache_hit_rate",
    "queue_depth",
    "background_jobs",
    "publication_duration_ms",
    "workspace_load_ms",
    "graph_update_ms",
    "api_errors",
    "authentication_failures",
    "active_traces",
    "error_rate",
)

ALERT_RULES = (
    "p95_latency_exceeded",
    "queue_backlog",
    "redis_unavailable",
    "publication_failures",
    "authentication_spike",
    "cache_miss_surge",
    "dependency_unavailable",
    "worker_failures",
)

P95_LATENCY_ALERT_MS = 2000
QUEUE_BACKLOG_ALERT = 25
AUTH_FAILURE_SPIKE = 10
CACHE_MISS_SURGE_RATE = 0.85

REQUIRED_LOG_FIELDS = (
    "timestamp",
    "correlation_id",
    "trace_id",
    "component",
    "severity",
    "message",
)
