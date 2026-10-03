# PR Audit — Sector Historical Percentile Verification (HVIE / UVE)

**Date:** 2026-08-04  
**Branch:** `cursor/sector-historical-percentile-audit-4cc0`  
**Verdict:** The 50–52 heatmap cluster is **not genuine historical valuation analysis**. It is the mathematical result of aggregating **within-sector peer ranks**.

---

## 1. Root Cause

### What the heatmap was computing

```text
warehouse.historical_valuation.percentile
  = cross-sectional peer rank within sector on PE
    (higher = cheaper vs peers today)

↓

market_intelligence_engine.aggregation.sector_table()
  historical_percentile = median(company peer percentiles)

↓

Sector heatmap
```

### Why every sector lands near 50–52

Within each sector, peer-rank percentiles are approximately uniform on [0, 100] **by construction**.  
The **median of a within-sector rank distribution is ≈ 50**.

Therefore:

| Sector | Median of peer ranks |
| --- | --- |
| Energy | ~50–52 |
| IT | ~50–52 |
| Financials | ~50–52 |
| … | ~50–52 |

Slight 50–52 drift comes from ties, missing PE, odd company counts, and rounding — **not** from a hard-coded `return 50`.

### What it should have been

```text
Historical Prices + Statements + Corporate Actions
        ↓ HVIE
Company Historical PE/PB
        ↓
Daily Sector Median
        ↓
Historical Sector Median Time Series
        ↓
Rank(today's sector median)
        ↓
Sector Historical Percentile
```

That path was **not** wired into the heatmap. `historical_sector_medians` only fed **premium / historical median level**, not the percentile KPI.

---

## 2. Data Coverage

Local agent warehouse snapshot is empty (`wh_historical_valuation` / `wh_historical_sector_medians` = 0 rows), so production observation counts must be re-run against live warehouse:

```text
SELECT sector, COUNT(*), COUNT(DISTINCT symbol), COUNT(DISTINCT date)
FROM historical_valuation JOIN company_master …
```

**Code expectations:**

| Source | Role | Typical risk |
| --- | --- | --- |
| `historical_valuation.percentile` | Peer rank (feeds old heatmap) | Always mid-pack when medianed |
| `historical_sector_medians` | Weekly HVIE persist of sector median PE | Thin if weekly job rarely ran |
| Reconstruct from `historical_valuation` PE by date×sector | Fallback series builder (new) | Needs multi-year backfill |

If reconstructed observations are low → status `INSUFFICIENT_HISTORY`, percentile `null` (UI: `n/a`).

---

## 3. Calculation Verification

### A) Old (buggy) warehouse peer rank

```318:321:intelligence-engine/institutional_warehouse/backfill/valuation_history.py
cheaper = sum(1 for value in pool if value < pe)
percentile = round(100.0 - (100.0 * cheaper / len(pool)), 2)
```

Polarity: **higher = cheaper vs peers**.

### B) Old sector aggregation

```python
hist_median_pct = median([m["percentile"] for m in sector_members])
# → ≈ 50 for every sector
```

### C) HVIE company own-history (correct formula, was unused for sectors)

```53:56:intelligence-engine/historical_valuation_intelligence/statistics.py
def _percentile_of(value, values):
    return round(100.0 * sum(1 for v in values if v <= value) / len(values), 1)
```

Polarity: **higher = more expensive vs own history**.

### D) New sector formula (fix)

```text
Percentile = rank of today's sector median within historical sector medians
```

Implemented in `historical_valuation_intelligence/sector_percentile.py`.  
Minimum observations: **24**. Below that → `null` + reason (never 50).

---

## 4. Code Review — Fallbacks / Defaults

| Location | Behavior | Impact |
| --- | --- | --- |
| No hard `percentile = 50` for sectors | Confirmed | Cluster is structural, not a literal default |
| `aggregation.sector_heatmap` band 45–55 → grey | Visual “fair” band | Amplifies mid-pack look |
| `sve.research` sort `or 50` | Sort key only | Not displayed |
| `sve.rerating_board` `(pct or 50)` | Transition label heuristic | Not heatmap |
| UI `fmt(pct, 0)` | Display rounding | Not inventing values |
| UI null sort `\|\| 0` (pre-fix) | Sort only | Fixed to null-last on heatmap |

**No React path invents 50 for display.**

---

## 5. Warehouse Validation

| Check | Result |
| --- | --- |
| `historical_sector_medians` schema has percentile? | **No** — only `median_value`, `company_count`, `as_of` |
| HVIE weekly persist builds daily history? | **Weekly snapshot of latest cross-section** — series grows only as weeks accumulate |
| UVE computes sector heatmap %? | **No** — UVE has company own-history percentile only |
| Heatmap consumed UVE? | **No** — consumed MI median of warehouse peer ranks |

---

## 6. UI Validation

- Heatmap shows backend `historical_percentile` via `fmt(..., 0)` (display round only).
- After fix: null → `n/a` + tooltip reason; never paints 50.
- Hint text updated to “sector median vs its own history (HVIE)”.

---

## 7. Expected vs Actual (pre-fix)

| | Expected (own-history) | Actual (peer-rank median) |
| --- | --- | --- |
| IT | high dispersion (e.g. 70–85 if rich) | ~51 |
| Financials | independent of IT | ~50 |
| Energy | independent | ~52 |
| Stdev across sectors | typically ≫ 5 | **≪ 5** |

**Classification:** Incorrect aggregation / wrong semantic definition — **Bug**.

---

## 8. Fixes Required

| Issue | Category | Status |
| --- | --- | --- |
| Sector heatmap used median of peer ranks | **Bug** (incorrect aggregation) | Fixed — HVIE sector own-history rank |
| Insufficient history returned mid-pack look | **Bug** (coverage guard) | Fixed — `null` + `INSUFFICIENT_HISTORY` |
| Industry cards used same peer-median pattern | **Bug** | Fixed — refuse fallback; await industry series |
| Market snapshot median of company peer ranks | **Bug** | Fixed — median of sector own-history % |
| Thin `historical_sector_medians` series | **Missing rebuild / data** | Mitigated — reconstruct from `historical_valuation`; still needs deep backfill in prod |
| Company row `percentile` still peer-rank | **Known limitation** | Out of scope for sector heatmap; company HVIE pack remains the own-history source |
| Weekly-only persist cadence | **Missing rebuild** | Prefer daily sector median persist in HVIE runtime follow-up |

---

## 9. Success Criteria Answer

> Does the current heatmap reflect genuine historical valuation analysis?

**Before fix: No.** Values were driven by **incorrect aggregation** of cross-sectional peer ranks, which mathematically collapse to ~50. Not a literal `return 50`, and not HVIE own-history.

**After fix:** Heatmap KPI is rank of today’s sector median in the sector median history (HVIE polarity). If history is thin, it shows **Unavailable** rather than a fake mid-pack number.

---

## API / code touchpoints

- `historical_valuation_intelligence/sector_percentile.py` — series load + rank
- `market_intelligence_engine/aggregation.sector_table` — primary consumer
- `sector_valuation_explorer` sectors / market / industry medians
- UI `SectorValuationWorkspace` heatmap null handling
