# AGI Universe Learning — gather & learn all companies

After loading `EQUITY_L` / `NIFTYstocks` and the Nifty index CSVs, the backend can **continuously gather** filings, financials, and evidence and **learn** structured knowledge for every company — without asking per ticker.

## What runs

```text
Index CSVs + NIFTYstocks
  → Historical Depth queue (prioritised)
  → Continuous Gather → Learn (CGL)
  → Knowledge Factory / IEP / KIL soft wires
  → Institutional Coverage (ICC) over time
```

Priority order:

1. Nifty 50  
2. Nifty Next 50  
3. Nifty 100  
4. Nifty 200  
5. Nifty 500 (+ Midcap Select)  
6. Bank / Financial Services residual  
7. Full NSE trading book (~2,360)

## Start learning

### Default — Nifty 500 book first (recommended)

```bash
curl -X POST "$ENGINE/v1/universe-learning/bootstrap" \
  -H "Content-Type: application/json" \
  -d '{"scope":"nifty500","run_cgl":true,"slot":"overnight"}'
```

### Full NSE trading book

```bash
curl -X POST "$ENGINE/v1/universe-learning/bootstrap" \
  -H "Content-Type: application/json" \
  -d '{"scope":"all","run_cgl":true,"slot":"overnight"}'
```

### Knowledge Operations desk

```bash
POST /v1/koc/action  {"action":"bootstrap_universe_learning"}
# full book:
POST /v1/koc/action  {"action":"learn_universe","ticker":"ALL"}
```

Node BFF: `/api/intelligence/universe-learning/*`

## Watch progress

```bash
GET /v1/universe-learning/status
GET /v1/continuous-gather-learn/dashboard
GET /v1/knowledge-factory/historical-depth
```

CGL already runs on a background loop when `CONTINUOUS_GATHER_LEARN=true` (Render). Bootstrap **re-seeds the queue** from your index/trading lists and kicks an overnight cycle so gather starts immediately.

## Throughput (approx.)

~36 companies/cycle with default HD batch settings; overnight + backfill-until-complete drains the backlog over successive cycles. Raise `KF_HD_BACKFILL_BATCH` / `BATCHES_PER_CYCLE` carefully against engine RAM.
