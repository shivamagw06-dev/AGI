# Phase 7.4d — Upstox Full-Universe Bootstrap

One-shot (resumable) bootstrap that populates all ISIN-mapped companies into `warehouse.valuation_ratios` in ~30–40 minutes with adaptive throttling — **not** a replacement for the nightly scheduler.

## Pipeline

```text
Company Master → ISIN → Upstox key-ratios → Normalizer → DQIV → Warehouse
  → historical_valuation snapshot → Unified Valuation Engine → Market / Sector Intelligence
```

UI never calls Upstox. Admin talks to Node BFF only.

## Bootstrap vs nightly

| Mode | Role |
|------|------|
| **Bootstrap** (`/admin/upstox-bootstrap`) | Drain full ISIN queue once; stop when Pending/Running/Retry = 0 |
| **Nightly 18:15 IST** | Incremental maintenance (~80 names); **skips** while bootstrap is running |

## Batching & throttle

- Default batch **40**, concurrency **3**, pause **2s** (env-overridable)
- On HTTP **429** → increase pause, reduce concurrency, move company to **RETRY**
- Healthy batches gently decrease pause toward `minPauseMs`
- Retry backoff: 30s → 2m → 10m → 30m → **FAILED**

## Queue states

`PENDING | RUNNING | SUCCESS | FAILED | RETRY | SKIPPED`

Missing ISIN (~291) tracked separately with reasons — never silently dropped.

## API

| Method | Path |
|--------|------|
| GET | `/api/market/upstox-bootstrap/status` |
| GET | `/api/market/upstox-bootstrap/missing-isin` |
| GET | `/api/market/upstox-bootstrap/failures` |
| POST | `/api/market/upstox-bootstrap/start` |
| POST | `/api/market/upstox-bootstrap/stop` |
| POST | `/api/market/upstox-bootstrap/reset` |

Start body (optional): `{ "reset": false, "batchSize": 40, "concurrency": 3, "pauseMs": 2000 }`

## Admin UI

`/admin/upstox-bootstrap` — summary, ETA, queue, API health, throughput, missing ISIN, failures, live log.

## Warehouse tabs

- `bootstrap_runs` — append-only run summaries
- `ingestion_health` — per-source coverage health (ops)

## Env

| Variable | Default |
|----------|---------|
| `UPSTOX_BOOTSTRAP_BATCH` | 40 |
| `UPSTOX_BOOTSTRAP_CONCURRENCY` | 3 |
| `UPSTOX_BOOTSTRAP_PAUSE_MS` | 2000 |
| `UPSTOX_BOOTSTRAP_MIN_PAUSE_MS` | 1000 |
| `UPSTOX_BOOTSTRAP_MAX_PAUSE_MS` | 60000 |
| `UPSTOX_BOOTSTRAP_STATE_DIR` | `$KIP_DATA_DIR/upstox_bootstrap` |
| `UPSTOX_VALUATION_INCREMENTAL_BATCH` | 80 (nightly) |

## Completion

Bootstrap completes when Pending = Running = Retry = 0. Remaining companies only in Failed / Skipped / Missing ISIN. Nightly scheduler then owns steady-state refresh.
