# AGIB Continuous Gather → Learn v1.0

Convert existing historical gathering + learning architecture into a **continuously running production pipeline**.

This does **not** retrain an LLM. “Learn” means:

- extract structured knowledge from history  
- evaluate forecasts vs outcomes  
- archive calibration / accuracy memory  
- weight future analyst opinions using that memory  

## Activated components

| Component | Role in the loop |
| --- | --- |
| **LIDI collectors** | Live NSE/BSE/RBI/IR historical ingestion |
| **Knowledge Factory Historical Depth** | Incremental multi-year depth + packs |
| **FAA Background Collector** | Filings / IR / news off the Ask path |
| **Institutional Scheduler** | Morning DAG (`historical_update` → LIDI + KF HD) |
| **FVL** | Forecast validation → learning records |
| **FLE** | Calibration jobs + consult |
| **ILO** | Process memory (mirrored to durable CGL archive) |
| **CAL** | Soft confidence / governed proposals (no auto-deploy) |
| **ResearchDirector** | Injects historical accuracy memory before CIO synthesis |

## Loop

```
Collect → Validate → Clean → Store → Embed/Extract → Update knowledge
→ Generate signals → Evaluate forecasts → Learn → Update confidence → Archive
```

Schedules (IST):

| Slot | Hours (IST) | Work |
| --- | --- | --- |
| pre_market | 05:00–09:00 | Morning DAG + LIDI + KF HD |
| intraday | 09:00–16:00 | LIDI incremental |
| post_market | 16:00–20:00 | LIDI + KF HD + FAA refresh |
| overnight | 20:00–05:00 | KF HD + FAA + full learning loop |

## Feature flags

| Flag | Default (Render) | Meaning |
| --- | --- | --- |
| `CONTINUOUS_GATHER_LEARN` | `true` | Master switch |
| `CONTINUOUS_GATHER_LEARN_INTERVAL_SEC` | `1800` | Engine loop interval |
| `CONTINUOUS_MORNING_DAG` | `true` | Run Institutional Scheduler morning DAG |
| `CONTINUOUS_LIDI` | `true` | Enable LIDI in CGL |
| `CONTINUOUS_KF_HD` | `true` | Enable KF Historical Depth |
| `CONTINUOUS_FAA_REFRESH` | `true` | FAA refresh in post-market/overnight |
| `CONTINUOUS_LEARNING_LOOP` | `true` | FVL/FLE/ILO/CAL cycle |
| `CONTINUOUS_DIRECTOR_LEARNING` | `true` | Inject memory into ResearchDirector |
| `CONTINUOUS_HISTORICAL_BACKFILL` | `true` | Resumable Yahoo→HD batch backfill |
| `CONTINUOUS_BACKFILL_UNTIL_COMPLETE` | `true` | Keep draining until remaining=0, then maintenance |
| `CONTINUOUS_BACKFILL_ACTIVE_INTERVAL_SEC` | `300` | Faster CGL interval while backlog remains |
| `KF_HD_LIVE_COLLECTORS` | `true` | Live Yahoo OHLCV / corporate actions into HD |
| `KF_HD_BACKFILL_BATCH` | `12` | Entities processed per backfill batch |
| `KF_HD_BACKFILL_BATCHES_PER_CYCLE` | `3` | Batches drained per CGL wake |
| `KF_HD_TARGET_YEARS` | `15` | Completion threshold for an entity |

See also: [AGIB_CONTINUOUS_BACKFILL_UNTIL_COMPLETE.md](./AGIB_CONTINUOUS_BACKFILL_UNTIL_COMPLETE.md).
| `FAA_BACKGROUND_COLLECTOR` | `true` | Dedicated FAA thread (limit 2 / 900s) |
| `ASK_SLIM` | `true` | Ask still skips heavy live fan-out |
| `AIL_LIVE_FAA` | `false` | Ask never calls unbound FAA acquire |

See also: [AGIB_HISTORICAL_COVERAGE_PHASE1.md](./AGIB_HISTORICAL_COVERAGE_PHASE1.md).

Node wake timer: `CONTINUOUS_GATHER_LEARN_SCHEDULER=true` (keeps engine warm across Render sleeps).

## Persistence / checkpoints

- LIDI / KF HD: existing disk stores (`LIDI_STORE_ROOT`, `KF_HD_STORE_ROOT`)
- CGL archive: `CGL_STORE_ROOT` or `$KIP_DATA_DIR/continuous_gather_learn`
  - checkpoints (resume metadata)
  - knowledge extracts
  - durable learning archive
  - observability metrics

Set `CGL_STORE_ROOT=/var/data/kip/continuous_gather_learn` after the paid disk is attached.

## Mission Control

Dashboard board **Continuous Gather → Learn** shows:

- loop status / slot  
- last cycle OK + latency  
- knowledge extracts  
- learnings archived  
- LIDI / KF freshness  

Agent Map marks activated gather/learn components as **working** when CGL flags are on.

## APIs

- `GET /v1/continuous-gather-learn/health`
- `GET /v1/continuous-gather-learn/dashboard`
- `POST /v1/continuous-gather-learn/run`
- Node proxies under `/api/intelligence/continuous-gather-learn/*`

## Safety

- Failures in collectors **never block Ask**
- Ask API unchanged
- No automatic CAL rule deployment
- No LLM weight training
