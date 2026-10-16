# HVIE Continuous Runtime (Phase 8.3R)

**Status:** Implemented  
**Module:** `historical_valuation_intelligence/runtime.py`  
**Depends on:** Phase 8.3 HVIE + warehouse reconstruction + VPAE

## Philosophy

HVIE is a **persistent historical valuation service**, not an on-demand reconstruction tool.

1. **Bootstrap once** per company → seed `historical_valuation`
2. **Append one observation** each trading day after close
3. **Forward-rebuild** only from statement release date when results arrive
4. **Full reconstruct** only when corporate actions change the price/share chain
5. **Weekly** persist statistics / sector medians
6. **Monthly** health + repair

Ask / Terminal / Market Intelligence never calculate history — they query HVIE.

## Schedules

| Cadence | When | Action |
|---|---|---|
| Bootstrap drain | Gather worker loop | Seed unseeded companies in slices |
| Daily | **18:30 IST** weekdays (Node tick) | Append today's observation |
| Weekly | Sunday ~09:00 IST | Persist stats + sector medians |
| Monthly | 1st ~10:00 IST | Coverage / DQIV repair |
| Quarterly | On statement ingest (`hooks.after_statements_written`) | Forward rebuild release→today |
| Corporate action | On CA ingest (`hooks.after_corporate_actions_written`) | Full reconstruct for split/bonus/rights/buyback/merger/demerger |

## Warehouse tabs

| Tab | Role |
|---|---|
| `historical_valuation` | Append-only observations (source of truth) |
| `hvie_company_state` | Per-company lifecycle (PENDING → SEEDED → DAILY) |
| `historical_statistics` | Persisted window stats (weekly) |
| `historical_sector_medians` | Cross-section medians (weekly) |
| `research_timeline` | Threshold / regime-change events |

## APIs

```bash
GET  /v1/historical-valuation/runtime/status
POST /v1/historical-valuation/runtime/run   {"mode":"bootstrap|daily|weekly|monthly|forward|ca"}
POST /v1/historical-valuation/runtime/start
POST /v1/historical-valuation/runtime/stop
GET  /v1/historical-valuation/coverage-dashboard
```

Admin: `/admin/historical-valuation`

## Research triggers

Automatically written when:

- Percentile ≥ 90 → highest decile event  
- Percentile ≤ 10 → cheapest decile / research priority  
- Regime changes → regime changed event  
- Crosses historical median → median-cross event  

## Env flags

| Flag | Default | Meaning |
|---|---|---|
| `HVIE_RUNTIME` | true | Gather-worker continuous loop |
| `HVIE_RUNTIME_SCHEDULER` | true | Node 18:30 IST tick |
| `HVIE_RUNTIME_BATCH` | 15 | Bootstrap slice size |
| `HVIE_DAILY_BATCH` | 120 | Daily append batch |

## Non-goals

- No vendor historical-ratio download  
- No full-history recompute on daily ticks  
- No UI-side calculations  
