# AGIB Institutional Historical Data — Production Hardening

Architecture (PR #295–#298) is frozen. This change eliminates remaining **acquisition, persistence, quality, and coverage** bottlenecks.

## What shipped

### Persistence
- `CheckpointManager` / `QueuePersistence` / `ResumeManager`
- Atomic writes + `fsync` + cross-process file locks
- Crash recovery resets stuck `running` rows without restarting from zero
- Render keys: `KF_HD_STORE_ROOT`, `LIDI_STORE_ROOT`, `CGL_STORE_ROOT`, `KIP_DATA_DIR`

### Connectors
Every source exposes: `collect` · `validate` · `normalize` · `store` · `health` · `coverage`

| Connector | Addresses |
|-----------|-----------|
| BSE Corporate Actions | Multi-strategy parsers + diagnostics + repair |
| RBI Macro | Structured series catalogue + missing-series warnings |
| Financial Statements | Yahoo quoteSummary statements; **no fixtures in production** |
| Shareholding | NSE/BSE ownership (Promoter/FII/DII/MF/Public/Pledged) |
| IR Discovery | Auto hub discovery beyond hardcoded portals + doc intel |

### Backfill
- Chunked resumable enrichment (`company → time chunk → checkpoint`)
- Parallel workers retained from existing queue engine

### Mission Control
Historical Ops adds: Financial / Shareholding / IR coverage, repair queue, persistence & checkpoint status, storage usage, recovery counters.

### Production KPIs
Collector success · Financial/Shareholding/IR coverage · Avg years · Repair queue · Extracts · Embeddings · Storage · Drain rate · Completeness

## Ops checklist

1. Attach Render disk at `/var/data/kip`
2. Set `KIP_DATA_DIR=/var/data/kip` (and optional store roots)
3. Keep `KF_HD_FIXTURE_QUARTERLY=false` and `KF_HD_LIVE_COLLECTORS=true`
4. Watch Mission Control Historical Ops for 7 days

## Explicit non-goals

No new analysts · No ResearchDirector redesign · No LLM retrain · No orchestration rewrite
