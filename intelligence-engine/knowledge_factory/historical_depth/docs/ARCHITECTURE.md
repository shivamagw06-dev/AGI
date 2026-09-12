# Historical Depth — Architecture (Sprint 4)

**Status:** Knowledge Factory enrichment only  
**Reasoning Architecture:** Frozen v1.0 (Phases 1–7 untouched)  
**Version:** `historical-depth-v1.0.0`

## 1. Architecture

```
Knowledge Factory
    ↓
Historical Collectors (fixture-first)
    ↓
Historical Validation (PIT / duplicates / completeness)
    ↓
Historical Derived Producers (recompute ratios — never store)
    ↓
Historical Company / Sector / Macro Objects
    ↓
Historical Evidence Packs
    ↓
Soft adapter → existing Institutional Evidence producers
    ↓
Existing Phases 1–7 (unchanged)
```

## 2. Folder structure

```
knowledge_factory/historical_depth/
  schema.py
  store.py                 # append-only HD store
  validators.py
  collectors/
  producers/derived.py
  objects/{company,sector,macro}.py
  packs.py
  queries.py
  time_travel.py           # PIT guarantee
  pipeline.py
  dashboard.py
  fixtures/seed_history.py
  docs/ARCHITECTURE.md
```

Store root: `data/knowledge_factory/historical/` (`KF_HD_STORE_ROOT`).

## 3. Historical database schema

Append-only JSON series files:

| Path | Contents |
|------|----------|
| `prices/{ENTITY}.json` | monthly OHLCV-like adj_close + returns |
| `financials_annual/{ENTITY}.json` | FY primitives with `available_from` |
| `financials_quarterly/{ENTITY}.json` | quarterly primitives + PIT |
| `corporate_actions/{ENTITY}.json` | dividends / bonus / buybacks |
| `timeline/{ENTITY}.json` | chronological events |
| `regimes/MARKET.json` | market regime windows |
| `macro/GLOBAL.json` | macro snapshots by period |
| `objects/{company,sector,macro}/` | compiled knowledge objects |
| `packs/` | historical evidence packs |
| `reports/` | pipeline + depth coverage |

**Point-in-time fields (mandatory):**

- `period`, `period_end`, `available_from`, `payload`, `source`, `confidence`
- Query filter: `available_from <= as_of` — **no look-ahead**

## 4–6. Object schemas

See compilers in `objects/`. Company objects include current/historical states, timeline, valuation, accounting, quality, risk, macro exposure, PE percentiles. Sector objects store historical median PE/PB/ROIC, winners/losers, cycles. Macro objects store rates/inflation/oil/FX/GDP/PMI/credit/liquidity + regimes.

## 7. Historical pipeline

`run_historical_pipeline(entities?)`:

Collect → Validate → Derive → Company objects → Packs → Macro → Sector objects → Depth dashboard

Also: `POST /v1/knowledge-factory/historical-depth/run`  
Track-1 daily may opt-in via `run_daily_pipeline(historical_depth=True)`.

## 8. Dashboard / North Star

`GET /v1/knowledge-factory/historical-depth`

Tracks average/median years, companies >10/15/20y, annual/quarterly completeness, evidence quality, validation failures, PIT integrity flag.

## 9. Acceptance tests

`tests/test_historical_depth.py` — valuation 2008, compare 2015/2025, PE>90th, crisis drawdown, rate-hiking cycles, replay 2020-03-31 (no April leakage), transparent insufficiency.

## 10. Migration plan

1. Deploy HD package (no Phase changes).
2. Nightly: `historical-depth/run` after Track-1 daily.
3. Soft adapter already prefers HD series when present.
4. Do not backfill by overwriting — append-only merge by `(period, available_from)`.
5. Next roadmap KPI after Depth green: **Sector Intelligence**.

## Point-in-time integrity guarantee

Analysing INFY as of **2020-03-31** excludes:

- FY20 annual (`available_from=2020-07-15`)
- FY20Q4 quarterly (`available_from=2020-04-20`)
- Any timeline/corporate action dated after as_of

`time_travel.state_as_of` returns an integrity audit and `excluded_future_*` lists.
