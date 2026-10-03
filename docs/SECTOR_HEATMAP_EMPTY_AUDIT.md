# Sector valuation heatmap empty — root cause

**Date:** 2026-08-04  
**Branch:** `cursor/sector-heatmap-empty-4cc0`

## Verdict

The heatmap is not missing API rows. All sectors return, but every cell shows **n/a** because `historical_percentile` is `null` with status `INSUFFICIENT_HISTORY`.

That status is correct after PR #508 (peer-rank ≈50 removed). The remaining bug is that reconstruction only saw **~2 dated sector medians** per sector — not because warehouse history is only two days deep, but because the reader hit the warehouse **5 000-row clamp**.

## Chain

1. Heatmap KPI = HVIE own-history percentile (need ≥24 dated sector medians).
2. `historical_sector_medians` persist table is empty (weekly HVIE job not filling it).
3. Fallback rebuilds series from `historical_valuation` PE × date × sector.
4. Rebuild used `store.all_rows(..., limit=50000)`, but `store.MAX_LIMIT = 5000`.
5. First 5 000 valuation rows ≈ **2 as-of dates** at universe scale → every sector reports `observation_count: 2` → UI `n/a`.

Same class of bug as Upstox coverage dashboard (#509).

## Fix

- Page `historical_valuation` / `company_master` / `historical_sector_medians` past `MAX_LIMIT`.
- One-pass reconstruction cache so sector_table does not re-scan ~87k rows per sector.
- Heatmap cells show observation count when percentile is unavailable.

## Still required for durable heat

- Run / keep HVIE weekly `persist_sector_medians` so `historical_sector_medians` is populated.
- Continue historical PE backfill so multi-year series exist (paging alone cannot invent missing years).
