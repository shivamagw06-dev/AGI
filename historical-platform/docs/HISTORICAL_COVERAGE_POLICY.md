# Historical Coverage Policy — Sprint 8.1

**Service:** HIP / HAP  
**Purpose:** Make historical completeness explicit, consistent, and measurable.

---

## 1. Policy principle

Every company in the historical universe is ingested to the **same coverage targets**. Completeness is reported per company / category so gaps are visible to Mission Control and ops.

---

## 2. Coverage targets

| Category | Target | Notes |
|---|---|---|
| **Daily OHLCV** | Maximum available history from Yahoo Finance | Prefer full chart history; minimum 10 years when available |
| **Weekly / Monthly OHLCV** | Derived or fetched for full available span | Same span as daily when possible |
| **Quarterly financials** | Maximum available history per company | Income statement series |
| **Annual financials** | Maximum available history per company | Prefer ≥ 10 fiscal years |
| **Balance sheets** | Maximum available quarterly/annual history | Never overwrite prior periods |
| **Cash-flow statements** | Maximum available quarterly/annual history | Never overwrite prior periods |
| **Earnings history** | Full available earnings dates + results | Links to financial periods |
| **Dividends** | Full available dividend history | Corporate action family |
| **Stock splits** | Full available split history | Corporate action family |
| **Corporate actions** | Full available history (NSE/BSE/Yahoo) | Versioned; corrections append |
| **Corporate announcements** | All available from NSE/BSE | Archived raw + canonical event |
| **Company IR reports** | Every available annual / quarterly / presentation / transcript / ESG / governance report | Retain all; never delete |
| **Historical company information** | Latest snapshot + prior profile versions when source provides them | Profile history is versioned |
| **Historical news metadata** | Maximum available metadata window | Full article bodies optional later |
| **Earnings calendar history** | Full available calendar | Used by AKO event boosts later |
| **Analyst recommendations / price targets** | Maximum available history where Yahoo exposes it | Lower confidence when single-source |
| **Index constituents** | Full available history if source provides it | NIFTY50 / sector indices |

---

## 3. Completeness score

For each company and category:

```text
completeness = periods_present / periods_expected
```

- `periods_expected` comes from the coverage target (e.g. quarters from FY2015→present).  
- `periods_present` counts distinct effective periods stored.  
- Status: `Complete` (≥95%), `Partial` (50–95%), `Sparse` (<50%), `Missing` (0%).

---

## 4. Ingestion modes

| Mode | Behaviour |
|---|---|
| **Bootstrap bulk** | One-time (or rare) full-history pull for a symbol/category |
| **Incremental historical** | Fetch only periods newer than last stored effective date |
| **Correction append** | New version with same effective date; prior version retained |

Never continuous live polling (that remains Phase 6 AKO/KAIP).

---

## 5. Universe (Sprint 8.1 seed)

Default watchlist: `INFY`, `RELIANCE`, `TCS`, `HDFCBANK`  
Configurable via `HIP_WATCHLIST`.

---

## 6. Non-goals for 8.1

- Tick-level / intraday historical bars  
- Alternative data vendors beyond Yahoo / NSE / BSE / Company IR  
- Timeline Intelligence (Sprint 8.3) and Pattern Intelligence (Sprint 8.5)
