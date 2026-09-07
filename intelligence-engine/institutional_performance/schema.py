"""PRP-01 — Performance & Scale constants."""

from __future__ import annotations

PRP_WORKSTREAM_ID = "PRP-01"
PRP_01_ID = PRP_WORKSTREAM_ID
PRP_PRODUCT = "Performance & Scale"
PRP_VERSION = "prp-01-v1.0.0"
PRP_SPEC = "docs/AGI_PRP_01_PERFORMANCE_SCALE.md"
PRP_ROLE = "production_readiness_performance"
PERF_ENGINE_VERSION = "prp-01-perf-v1"

# Architecture freeze: PRP does not add intelligence engines
ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"

CACHE_NAMESPACES = (
    "query",
    "object",
    "workspace",
    "publication",
    "graph",
)

DEFAULT_TTLS = {
    "query": 120,
    "object": 300,
    "workspace": 60,
    "publication": 600,
    "graph": 180,
}

# Success targets
TARGET_ASK_CACHED_MS = 2000
TARGET_WORKSPACE_MS = 1000
TARGET_CONCURRENT_USERS = 100

LATENCY_TARGET_SECONDS = {
    "ask": TARGET_ASK_CACHED_MS / 1000.0,
    "ask_cached": TARGET_ASK_CACHED_MS / 1000.0,
    "workspace": TARGET_WORKSPACE_MS / 1000.0,
    "parallel_orch": 2.0,
    "graph_incremental": 1.0,
    "publication_generate": 5.0,
}

JOB_KINDS = (
    "publication_generate",
    "graph_incremental",
    "cache_warmup",
    "orchestrate_parallel",
)

SLOW_QUERY_MS = 1500
