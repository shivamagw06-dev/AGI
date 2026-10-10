# AGIB Institutional Historical Data Coverage — Phase 1

**Objective:** Maximise historical coverage using existing LIDI, Knowledge Factory, FAA, and Continuous Gather → Learn. No new analyst agents. No ResearchDirector redesign. No LLM retrain.

## What shipped

### 1. BSE Corporate Actions
- Resilient parsers: CSV, JSON API shapes, HTML tables, regex fallback
- Classifies dividends / splits / bonus / rights / buybacks
- Append-merge durable history + QA metrics (`live_data/qa.py`)

### 2. RBI DBIE / key rates
- HTML extraction for repo, reverse repo, CRR, SLR, CPI, WPI, IIP, GDP, FX reserves, G-Sec, credit/deposit growth
- Incremental series history + bridge into KF HD macro store

### 3. Company IR
- Discovers PDF / office docs from IR hubs + secondary pages
- Classifies annual reports, quarterly results, presentations, transcripts, ESG, ratings, press
- Dedupes by URL / checksum; optional bounded downloads

### 4. Knowledge Factory Historical Depth
- Live Yahoo monthly OHLCV + corporate actions (`KF_HD_LIVE_COLLECTORS=true`)
- Resumable backfill engine with checkpoints (`historical_backfill_checkpoint`)
- Batching, cooldown on repeated failures, skip completed entities
- Coverage dashboard uses max(annual periods, price span years)

### 5. CGL Historical Backfill
- Overnight / post-market batch via `CONTINUOUS_HISTORICAL_BACKFILL`
- Structured knowledge extracts (CAGR, drawdowns, vol, debt trend, …) into CGL store

### 6. Mission Control
- Continuous Gather → Learn board shows:
  - Historical coverage %
  - Average years / company
  - Fully backfilled + backlog
  - IR documents
  - Collector success rate / ETA

### 7. FAA Background
- Remains Ask-isolated; enabled in `render.yaml` (`FAA_BACKGROUND_COLLECTOR=true`) after collector hardening

## Production flags (`render.yaml`)

| Flag | Value |
|------|-------|
| `CONTINUOUS_GATHER_LEARN` | true |
| `CONTINUOUS_KF_HD` | true |
| `CONTINUOUS_HISTORICAL_BACKFILL` | true |
| `KF_HD_LIVE_COLLECTORS` | true |
| `KF_HD_BACKFILL_BATCH` | 12 |
| `KF_HD_TARGET_YEARS` | 15 |
| `FAA_BACKGROUND_COLLECTOR` | true |

## Success trajectory

Coverage grows incrementally (≈12 companies / overnight cycle by default). Mission Control should trend toward:

- Historical coverage → 95%+
- Average company history → 10–20y
- Corporate actions / macro series complete
- Knowledge extracts and forecast learning growing daily

## Constraints respected

- No new analyst agents
- No ResearchDirector redesign
- No LLM retraining
- Ask path remains isolated (`ASK_SLIM`, `AIL_LIVE_FAA=false`)
