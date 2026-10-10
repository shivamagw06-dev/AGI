# Audit — Upstox Fundamentals Coverage Dashboard

**Date:** 2026-08-04  
**Branch:** `cursor/upstox-coverage-dashboard-audit-4cc0`  
**Constraint:** Do **not** rerun bootstrap until root cause is confirmed — confirmed below.

---

## Verdict

| Question | Answer |
| --- | --- |
| Data loss? | **No** — warehouse still holds Upstox key-ratios and master data |
| Wrong database? | **No** — same IE warehouse that reports 2,706 companies |
| Bootstrap metadata reset? | **Partially** — Node in-memory queue can show 0 after redeploy; warehouse `bootstrap_runs` retained |
| PR #508 caused this? | **No** — #508 only changed sector historical percentile |
| Real cause? | **Dashboard calculation bug** in Coverage Health (#507): `store.all_rows` is hard-capped at **5,000** rows |

---

## What the UI was showing

The labels **Universe / ISIN / Bootstrapped / No Upstox Fundamentals** come from the **Coverage Health** panel on Valuation Terminal (`CoverageHealthPanel.jsx` from PR #507), not from the UIFI admin page alone.

| UI field | Source API | Field |
| --- | --- | --- |
| Universe / ISIN / Bootstrapped | `GET /api/market/upstox-bootstrap/status` | `summary.companies`, `isinAvailable`, `completed` |
| No Upstox Fundamentals | `GET /api/intelligence/valuation/coverage/health` | `residual_gap.no_upstox_fundamentals` |

---

## Live warehouse row counts (production IE)

Queried `GET /v1/warehouse/coverage` + paged tab reads on 2026-08-04:

| Table | Rows | Notes |
| --- | --- | --- |
| `company_master` | **2,706** | With ISIN **2,415** (89.25%) |
| `valuation_ratios` | **18,940** | All `source=upstox`; **2,077 distinct symbols** |
| `financials_annual` | **10,012** | Sources: formula_engine / financial_connector (not UIFI) |
| `financials_quarterly` | **12,638** | Same |
| `ownership` | **8,599** | `knowledge_factory_hd` (not `upstox`) |
| `profile_history` | **0** | UIFI profile bootstrap not populated |
| `peer_relationships` | **0** | UIFI competitors not populated |
| `corporate_actions` | **14,788** | Mostly non-Upstox primary feeds |
| `bootstrap_runs` | **2** | Includes a **100%** key-ratios run (`success=2415`) |
| `daily_market_history` | **948,000** | Intact |
| `historical_valuation` | **86,922** | Intact |

**Conclusion:** Key-ratios bootstrap work from #495–#497 is present. UIFI (#502) statement/ownership/profile tabs were either never written with `source=upstox` or not run to completion — that is separate from the “No Upstox Fundamentals=1823” figure.

---

## Exact queries / code paths

### 1) Residual “No Upstox Fundamentals” (buggy)

```145:178:intelligence-engine/institutional_coverage_health/production.py
# BEFORE fix:
ratio_rows = store.all_rows("valuation_ratios", limit=50000) or []
```

But:

```31:31:intelligence-engine/institutional_warehouse/store.py
MAX_LIMIT = 5000
```

```229:229:intelligence-engine/institutional_warehouse/store.py
limit = max(1, min(int(limit or 200), MAX_LIMIT))
```

So only the **first 5,000** `valuation_ratios` rows are scanned (alphabetical from `20MICRONS…`) → **295 symbols**.

Then residual:

```python
# masters with ISIN but not in provider_by_symbol
no_upstox_fundamentals ≈ 2415 - 295 = 2120
```

That matches the live Coverage Health response (`no_upstox_fundamentals: 2120`).  
User’s **1823** is the same bug class (timing/cache/progress differed slightly).

**True gap after full scan:**

```text
ISIN available          2,415
Distinct ratio symbols  2,077
True “no key-ratios”      338
```

### 2) Bootstrap Universe / ISIN / Bootstrapped (=0)

```478:498:server/services/upstoxBootstrapEngine.js
summary: {
  companies: run.masters,
  isinAvailable: run.withIsin,
  completed: counts.SUCCESS || 0,
  ...
}
```

State is **Node process memory + optional `state.json`**. After Render redeploy, until the queue is rebuilt, UI can show **0 / 0 / 0** even while warehouse ratios remain.

Warehouse truth (`bootstrap_runs`):

| run_id | success | coverage | ended |
| --- | --- | --- | --- |
| `ubr-b0124c30a1f4` | **2415** | **100%** | 09:57 UTC |
| `ubr-d1c0639fe352` | 994 | 41.2% | 13:45 UTC (paused / restarting) |

Live Node status at audit time: `paused`, companies=2706, ISIN=2415, SUCCESS=994 — **not** zeros now. Zeros = metadata/ephemeral queue, not wiped warehouse.

### 3) UIFI coverage (`GET /api/upstox/coverage` → `/v1/upstox-fundamentals/coverage`)

Uses `store.fetch(..., filters={source: "upstox"}, limit=1).total` — **totals are correct** (not capped for counting):

| Metric | Value | Meaning |
| --- | --- | --- |
| companies | 2706 | OK |
| with_isin | 2415 | OK |
| valuation_ratios | 18940 | OK |
| statements_* / ownership / profiles / competitors | **0** | No rows with `source=upstox` (data may exist under other sources) |

---

## PR #508 impact

PR #508 changed **sector historical percentile** aggregation only.  
It does **not** touch `valuation_ratios`, bootstrap status, or residual gap math.

PR **#507** introduced Coverage Health residual/bootstrap panels and the truncated `all_rows` scan.

---

## Classification

| Symptom | Classification |
| --- | --- |
| No Upstox Fundamentals ≈ 1800–2100 while 18.9k ratio rows exist | **Dashboard calculation bug** (5k row cap) |
| Universe/ISIN/Bootstrapped = 0 after redeploy | **Metadata / ephemeral Node state** |
| UIFI statements/ownership/profiles = 0 | **Missing UIFI ingest** (or wrong source tag) — not key-ratios loss |
| Warehouse empty? | **False** |

---

## Fix (this branch)

- Page `store.fetch` with `offset` in Coverage Health (`_paged_rows`)
- Rebuild `_provider_ratio_index` / `_annual_index` from full paged reads
- Regression test: second page symbols must appear in the provider index

**Do not rerun bootstrap** to “fix” the 1823 figure — warehouse already has ~2,077 ratio symbols; rerunning only burns API quota.

---

## Recommended ops checks (read-only)

1. Refresh Coverage Health after this fix deploys → expect `no_upstox_fundamentals` ≈ **338**, `key_ratios` ≈ **2077**
2. Prefer `bootstrap_runs` + `valuation_ratios` distinct symbols over Node queue for historical truth
3. Treat UIFI zeros as a separate Phase 7.4E completion task (source=`upstox` writes), not as key-ratios failure

---

## Note — `upstox_key_ratios_empty` in bootstrap logs

This error is returned by `refreshUpstoxValuationRatios` when **zero** companies in a batch successfully fetch from Upstox (every call threw). Live bootstrap failures show `Too Many Request Sent` (HTTP **429**) on the same batches.

So the log line is usually **rate-limit**, not “Upstox has no key-ratios for this ticker.” Warehouse already holds tens of thousands of ratio rows; pause/resume bootstrap rather than treating this as data emptiness.

After this branch: the same condition surfaces as `upstox_rate_limited` (with legacy alias retained).
