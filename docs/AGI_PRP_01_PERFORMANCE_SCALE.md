# PRP-01 — Performance & Scale

Production Readiness Programme workstream 1. Make AGIB fast enough for institutional use.

## Status

AGIB intelligence architecture is **frozen at v1.0**. PRP-01 does **not** add knowledge, decision, risk, committee, or portfolio engines.

## Mission

| Target | Goal |
|--------|------|
| Ask AGI (cached) | &lt; 2 seconds |
| Workspace | &lt; 1 second |
| Publication generation | Asynchronous |
| Concurrent users | 100+ |

## Package

`intelligence-engine/institutional_performance/`

## Build

| Capability | Implementation |
|------------|----------------|
| Distributed cache | Redis when `REDIS_URL` / `AGI_PRP_REDIS`; in-memory fallback |
| Query cache | Namespace `query` — soft-hooks UAG `ask` |
| Object cache | Namespace `object` |
| Workspace cache | Namespace `workspace` — soft-hooks RW company/portfolio |
| Publication cache | Namespace `publication` |
| Graph cache | Namespace `graph` — incremental invalidation over KG-01 |
| Parallel orchestration | Thread-pool `run_parallel` (`AGI_PRP_PARALLEL_ORCH`) |
| Async publication | Job queue kind `publication_generate` when `async: true` |
| Background job queue | In-process `ThreadPoolExecutor` workers |
| Incremental graph updates | Invalidate + soft neighbourhood refresh; KG-01 remains SoR |
| Streaming | NDJSON event envelope helpers for progressive Ask |

## Mission Control — Performance Center

Soft-slice key: `institutional_performance`

- Cache hit rate
- P95 latency
- Slow queries
- Queue depth
- Active workers

## API

- `GET /v1/performance/health`
- `GET /v1/performance/metrics`
- `GET /v1/performance/cache`
- `POST /v1/performance/cache/get|set`
- `GET /v1/performance/queue`
- `GET/POST /v1/performance/jobs`
- `GET /v1/performance/jobs/{job_id}`
- `POST /v1/performance/graph/incremental`
- `POST /v1/performance/parallel`

## Flags

| Env | Default | Meaning |
|-----|---------|---------|
| `AGI_PRP_01_ENABLED` | true | Master switch |
| `AGI_PRP_REDIS` | true | Attempt Redis |
| `AGI_PRP_PARALLEL_ORCH` | true | Parallel fetches |
| `AGI_PRP_ASYNC_PUB` | true | Allow async publications |
| `AGI_PRP_QUERY_CACHE` | true | Cache Ask results |
| `AGI_PRP_WORKSPACE_CACHE` | true | Cache workspaces |
| `AGI_PRP_MAX_WORKERS` | 8 | Queue / parallel workers |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |

## Soft integrations

- **UAG-01** — query cache on `ask` (`bypass_cache` to skip)
- **RW-01** — workspace cache on company/portfolio assemble
- **PUB-01** — `generate({ async: true })` enqueues job; poll job status

## Invariants

- Does not analyze markets or invent recommendations
- Does not own a second knowledge graph
- Does not replace PCE / CIO / ICE / PRE policy or decision SoRs
- Architecture remains AGIB v1.0
