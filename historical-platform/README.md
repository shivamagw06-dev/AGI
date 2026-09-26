# AGI Historical Intelligence Platform (HIP)

**Phase 8** — permanent historical memory for institutional reasoning across decades.

| Phase | Role |
|---|---|
| Phase 6 (KAIP) | Live knowledge |
| **Phase 8 (HIP)** | Historical knowledge |

## Sprint 8.1 — Historical Acquisition Platform (HAP)

Bulk historical ingestion → validate → normalize → resolve → versioned Historical Knowledge Store → retrieval APIs.

## Sprint 8.2 — Historical Knowledge Objects & Timeline Intelligence

Shape HKO views and build company / sector / market / macro **timelines** so Ask retrieves historical narratives, not rows.

## Sprint 8.3 — Historical Relationship Intelligence (HRI)

Evidence-backed **cause-and-effect** graph across companies, sectors, macro and market.

## Sprint 8.4 — Historical Analogue Intelligence (HAI)

**Crown jewel:** answer *“Have we ever seen this before?”* with ranked, explainable historical analogues.

Ask / Intelligence Engine must retrieve history **without** calling Yahoo, NSE, BSE, or Company IR.

## Contracts

- [`docs/HAP_PLATFORM_CONTRACT.md`](docs/HAP_PLATFORM_CONTRACT.md)
- [`docs/HISTORICAL_COVERAGE_POLICY.md`](docs/HISTORICAL_COVERAGE_POLICY.md)
- [`docs/HKO_TIMELINE_CONTRACT.md`](docs/HKO_TIMELINE_CONTRACT.md)
- [`docs/HRI_CONTRACT.md`](docs/HRI_CONTRACT.md)
- [`docs/HAI_CONTRACT.md`](docs/HAI_CONTRACT.md)
- Programme notes: [`../docs/HIP_SPRINT_8_2.md`](../docs/HIP_SPRINT_8_2.md), [`../docs/HIP_SPRINT_8_3.md`](../docs/HIP_SPRINT_8_3.md), [`../docs/HIP_SPRINT_8_4.md`](../docs/HIP_SPRINT_8_4.md)

## Pipeline

```text
Sources → Historical Collectors → Raw Historical Archive
→ Validation → Canonical Normalizer → Entity Resolution
→ Historical Knowledge Builder (HKO) → Timeline Builder
→ Historical Knowledge Store → Historical Retrieval API
```

## Collectors

- `YahooHistoricalCollector` — OHLCV, financials, dividends, splits, profile, news, analyst tips  
- `NSEHistoricalCollector` — bhavcopy, announcements, actions, index constituents  
- `BSEHistoricalCollector` — announcements, corporate actions  
- `CompanyIRHistoricalCollector` — annual/quarterly reports, presentations, transcripts, ESG, governance  

## History APIs (8.2–8.4)

```text
GET  /v1/history/company/{symbol}
GET  /v1/history/timeline/{symbol}
GET  /v1/history/financials/{symbol}
GET  /v1/history/events/{symbol}
POST /v1/history/compare
GET  /v1/history/mission-control
GET  /v1/history/relationships/company/{symbol}
GET  /v1/history/relationships/sector/{sector}
GET  /v1/history/relationships/macro/{event}
GET  /v1/history/relationships/market
POST /v1/history/relationships/explain
GET  /v1/history/analogues/company/{symbol}
GET  /v1/history/analogues/sector/{sector}
GET  /v1/history/analogues/market
GET  /v1/history/analogues/macro
POST /v1/history/analogues/search
```

## Run locally

```bash
cd historical-platform
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
HIP_LIVE_COLLECTORS=false uvicorn app.main:app --port 8092
```

Bootstrap (ops only — rebuilds timelines):

```bash
curl -X POST http://127.0.0.1:8092/v1/internal/bootstrap
curl http://127.0.0.1:8092/v1/history/timeline/INFY
curl -X POST http://127.0.0.1:8092/v1/history/compare \
  -H 'content-type: application/json' \
  -d '{"symbol":"INFY","as_of_period":"FY2018"}'
curl -X POST http://127.0.0.1:8092/v1/history/relationships/explain \
  -H 'content-type: application/json' \
  -d '{"source":"RBI Rate Cut","target":"HDFCBANK"}'
curl -X POST http://127.0.0.1:8092/v1/history/analogues/search \
  -H 'content-type: application/json' \
  -d '{"scope":"company","entity":"INFY","question":"Has Infosys experienced this type of slowdown before?","top_k":5}'
```

## Tests

```bash
cd historical-platform && pytest -q
```

## Boundary

Historical store is append-only and separate from live KAIP. Corrections create new versions. Timeline narratives may be regenerated; HKO facts are never overwritten. Retrieval APIs always return `providers_queried: []`.
