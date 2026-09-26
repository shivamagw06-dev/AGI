# Phase 8.3A — HVIE Universe Completion Programme

**Module:** `intelligence-engine/historical_valuation_intelligence/universe_programme/`  
**Admin:** `/admin/hvie-runtime`  
**APIs:** `/v1/hvie/runtime/*` (BFF: `/api/intelligence/hvie/runtime/*`)

## Problem

Historical Intelligence coverage was ~4.6% because only ~145 / 2706 companies had completed the HVIE pipeline. The engine was correct; the universe was incomplete, and bootstrap state was not durable across redeploys.

## Design

- **Never** download vendor historical PE / PB / EV.
- Reconstruct from warehouse: `daily_market_history` + `financials_*` + `corporate_actions` + VPAE.
- Persist every company in `hvie_universe_queue` (not in-memory).
- Bootstrap continues until `pending = running = retry = 0`.
- Waiting on prices/statements → `SKIPPED` with `WAITING_*` lifecycle (re-promoted when inputs arrive).
- After complete → continuous daily append / statement forward / CA full rebuild (existing HVIE runtime).

## Queue statuses

`PENDING · RUNNING · COMPLETED · RETRY · SKIPPED · FAILED`

## Lifecycle

`NOT_STARTED · READY · WAITING_PRICE_HISTORY · WAITING_STATEMENTS · WAITING_CORPORATE_ACTIONS · RUNNING · FAILED · COMPLETE`

## Pipeline stages

classify → prices → statements → corporate_actions → reconstruct → statistics → percentile → bands → regime → research → complete

## New warehouse tabs

- `hvie_universe_queue`
- `historical_industry_medians`
- `historical_market_medians`

## Coverage Health

`GET /v1/valuation/coverage/health` now includes `hvie_pipeline` / `hvie_pipeline_dashboard` stage counts so the UI shows where the pipeline stops, not only a single Historical Intelligence %.

## Success targets

See programme brief — >95% percentiles/bands/regimes/research on eligible names; sector/industry/market medians persisted; daily append >99%.
