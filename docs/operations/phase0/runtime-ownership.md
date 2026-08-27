# AGI Runtime Ownership Map

One recurring operation must have exactly one production owner.

| Capability | Production owner | Process | Persistent output | Phase 0 state |
|---|---|---|---|---|
| Public product API, auth, cache | `agib-api` | Node web | Supabase/cache | Active |
| Live Alpha WebSocket and five intraday strategies | `agib-api` | Node web | Supabase | Active configuration |
| Hedge Fund live quotes/candles/snapshots | `agib-api` | Node schedulers | Supabase + engine API | Active configuration |
| Ask AGI and research reads | `agib-intelligence-engine` | Python web | KIP + warehouse | Active |
| KIP document/research memory | `agib-intelligence-engine` | Python web | Render disk, optional Supabase mirror | Active |
| Capital IQ bootstrap and resumable import | `agib-intelligence-engine` | Python web background jobs | Render disk warehouse | Active on demand/restart |
| Continuous Gather and Learn | Disabled | No active owner | Existing warehouse retained | Intentionally disabled; historical coverage accepted |
| FAA public evidence collector | Disabled | On-demand only | Existing KIP/FAA stores retained | Continuous collection not required |
| LIDI and historical-depth collectors | Disabled | No active owner | Existing LIDI/KF stores retained | Historical backfill complete enough for current use |
| Warehouse historical backfill | Disabled | No active owner | Institutional warehouse | Existing historical inventory retained |
| Historical valuation backfill | Disabled | No active owner | Warehouse HVIE tables | Existing valuation history retained |
| Forecast runtime | Disabled | On-demand/manual | Forecast warehouse tables | Existing forecasts retained; no continuous backfill |
| Company dossier generation | Disabled | No active owner | Warehouse/Supabase | Paused; health telemetry stale |
| Macro runtime | Disabled | No active owner | Macro warehouse tables | Disabled |
| E01 macro regime | Disabled | No active owner | EngineState store | Disabled |
| E02-E14 and L4 research engines | ORCH feature-ready consumers | Python runtime | Currently process-local/empty | Loaded, zero runs |
| E10 portfolio construction | Disabled | No active owner | Model portfolio store | Disabled |
| Validation/replay and CRE | Manual/API initiated | Python web/worker | Replay stores | Available, zero runs |
| CMS ingestion | `agib-api` or `agib-cms-ingest-worker` | Node embedded/external | Supabase | Blueprint says embedded |

## Ownership Rules

1. The Python web process serves reads and short control requests; it does not own gather loops.
2. The gather worker owns collection, backfill, forecast materialisation, and heavy maintenance.
3. Node owns broker connectivity and intraday market state.
4. A scheduler must never run simultaneously in Node, Python web, and Python worker.
5. Every owner writes a durable heartbeat, lease, last success, next run, and failure reason.
6. A health response may say `OPERATIONAL` only when its owner heartbeat and output freshness pass.

## Known Persistence Boundary

Render persistent disks are not shared between services. The Python worker must either:

- publish completed results to authenticated web APIs/Supabase, or
- use a shared database as its primary operational store.

Phase 1 must resolve this before claiming continuous intelligence is restored.
