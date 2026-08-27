# Historical Acquisition Platform (HAP) — Sprint 8.1

**Service:** AGI Historical Intelligence Platform (HIP)  
**Layer:** Historical Acquisition Platform  
**Version:** 0.1.0  
**Phase:** 8 — Historical Intelligence Platform  
**Complements:** Phase 6 KAIP (live knowledge)

---

## 1. Mission

> Build AGI's permanent historical memory by ingesting, validating, versioning and organising historical market, company, sector and macro information so the Intelligence Engine can reason across decades rather than only the present.

| Phase | Role |
|---|---|
| **Phase 6** | Live knowledge |
| **Phase 8** | Historical knowledge |

---

## 2. Boundary

HAP is **bulk ingestion followed by incremental historical updates**, not continuous polling.

HAP does **not**:
- Continuously poll like AKO/KAIP
- Perform reasoning / LLM / embeddings
- Overwrite historical records
- Serve Ask by calling Yahoo / NSE / BSE / Company IR

---

## 3. Pipeline

```text
Yahoo Finance / NSE / BSE / Company IR
              │
              ▼
     Historical Collectors
              ▼
     Raw Historical Archive
              ▼
  Validation & Quality Gates
              ▼
     Canonical Normalizer
              ▼
      Entity Resolution
              ▼
 Historical Knowledge Builder
              ▼
  Historical Knowledge Store
              ▼
   Historical Retrieval API
```

---

## 4. Historical Knowledge Object types (Sprint 8.1)

```text
HistoricalPriceHistory
HistoricalFinancialStatement
HistoricalBalanceSheet
HistoricalCashFlow
HistoricalCorporateEvent
HistoricalCorporateAction
HistoricalDividendHistory
HistoricalOwnershipHistory
HistoricalMarketSnapshot
HistoricalCompanyProfile
HistoricalNewsEvent
```

---

## 5. Storage (append-only, separate from live)

```text
historical_raw_archive
historical_prices
historical_financials
historical_balance_sheets
historical_cashflows
historical_dividends
historical_actions
historical_events
historical_reports
historical_company_profiles
historical_news
historical_metadata
historical_ingestion_runs
```

Nothing here is ever overwritten. Corrections are new versions.

---

## 6. Versioning / provenance (every record)

- Source  
- Retrieved timestamp  
- Effective date  
- Version  
- Checksum  
- Provenance / source event id  
- Ingestion run id  

---

## 7. Entity resolution

Every historical object resolves to:

- Company  
- Sector  
- Industry  
- Index membership  
- Time period (e.g. FY2019 Q3)

---

## 8. Historical integrity rules

1. Never modify historical records.  
2. Never overwrite past financial statements.  
3. Preserve original effective dates.  
4. Preserve source provenance.  
5. Record corrections as new versions.

---

## 9. Coverage policy

See [`HISTORICAL_COVERAGE_POLICY.md`](HISTORICAL_COVERAGE_POLICY.md). Coverage targets are measurable and applied uniformly per company in the watchlist / universe.

---

## 10. Success criteria

- Historical collectors ingest supported sources (fixture + live modes)  
- Raw historical data is archived  
- Records are validated  
- Canonical historical objects are generated  
- Entity resolution is applied  
- Versioned historical records are stored  
- Historical Retrieval APIs return company history **without** querying external providers  

### Success example

> “Show Infosys revenue growth from FY2015 to FY2025 and compare valuation during each earnings cycle.”

IE retrieves everything from the Historical Knowledge Store — zero Yahoo/NSE/BSE/IR calls on the Ask path.
