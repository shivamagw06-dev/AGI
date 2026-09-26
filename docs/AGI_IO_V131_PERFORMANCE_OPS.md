# AGI V1.3.1 — Performance & Operations (Morning Snapshot)

## Objective

Make the Institutional Morning Office feel instantaneous while preserving overnight analysis richness.

This is **not** a feature release. It separates **production pipelines** from **interactive dashboards**.

## Data classes

| Data | Freshness | Delivery |
|---|---|---|
| Morning brief | Once/day + manual refresh | Precomputed snapshot |
| Operational metrics (coverage, knowledge health) | 5–15 min | Cached aggregates inside snapshot |
| Live status (scheduler/job/flags) | Seconds | `/system-health` live API |

## Architecture

```text
CGL finishes → KIL soft-wire → Morning Snapshot Builder → disk/warm snapshot
Morning DAG READY → Morning Snapshot Builder → disk/warm snapshot
Browser → GET /overview → snapshot (50–300 ms target)
Admin → POST /refresh → async job (existing snapshot keeps serving)
```

Heavy ICF / IEP / CGL scans **do not** run because a user opened the page.

## Persist

`$KIP_DATA_DIR/investment_office/morning_snapshot.json`  
(fallback: `intelligence-engine/data/investment_office/`)

## APIs

| Method | Path | Behavior |
|---|---|---|
| GET | `/investment-office/overview` | Snapshot / placeholder (fast) |
| GET | `/investment-office/snapshot` | Snapshot metadata |
| GET | `/investment-office/system-health` | Live status only |
| POST | `/investment-office/refresh` | Queue rebuild (`wait:true` for sync ops) |
| POST | `/investment-office/generate-morning-brief` | Queue brief regeneration |

## Soft hooks

1. End of `continuous_gather_learn.orchestrator.run_cycle` after KIL  
2. `InstitutionalScheduler.run_morning` when `system_ready` (beside Research Office)

## SLOs

| Endpoint | Target |
|---|---:|
| `/overview` | <300 ms (warm snapshot) |
| `/system-health` | <500 ms |
| `/refresh` | Async job; snapshot keeps serving |

## Success criteria

- Cold `/overview` under 1s when a snapshot exists (excluding infra cold starts)
- Warm `/overview` under 200–300 ms
- Heavy ICF/IEP/CGL removed from the synchronous request path
- Snapshot automated after overnight/morning pipeline; refreshable by admin

## Version

- `io-v1.3.1`
- Platform: `AGI V1.3.1`
