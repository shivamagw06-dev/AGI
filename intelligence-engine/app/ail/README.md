# AGIB Intelligence Layer V2 (AIL)

**Architecture status:** v1.0.1 LOCKED  
**Position:** after FAA/FRE · before CAE / Ask AGI  
**Role:** transform retrieved evidence into living institutional investment intelligence.

```text
FAA (Acquire) → FRE (Retrieve) → AIL (Intelligence) → CAE → Ask AGI
```

AIL does **not** redesign FAA, FRE, CAE, or Ask AGI.

## Systems

| Code | Name | Responsibility |
|------|------|----------------|
| CDE | Company Dossier Engine | Incremental living dossiers with Evidence IDs |
| EDE | Event Detection Engine | Corporate event detection → timeline |
| TE | Thesis Engine | Bull / Base / Bear with explainable probability updates |
| PE | Prediction Engine | Distributional forecasts; immutable versions |
| CME | Continuous Monitoring Engine | Watchlists + institutional cadences |
| EL | Evidence Ledger | Immutable claim registry — provenance required |

Plus Timeline Engine, Knowledge Graph extensions, and Audit trail.

## APIs

- `GET /v1/ail/health|dashboard|analyse`
- `POST /v1/ail/monitor/run`
- `GET /v1/company/{ticker}/dossier|timeline|events|thesis|forecast|ledger|monitor`
- `GET /v1/event/{id}` · `/v1/evidence/{id}` · `/v1/prediction/{id}`

BFF: `/api/intelligence/...`

## Soft-wire

Ask AGI `UiService.search` soft-calls `AilService.package_for_ask_agi`.  
Optional bind to FAA/FRE when those layers are present (`faa_bound` / `fre_bound` in health).

## Flags

`AIL`, `AIL_CDE`, `AIL_EDE`, `AIL_TE`, `AIL_PE`, `AIL_CME`, `AIL_EL`, `AIL_GRAPH`, `AIL_TIMELINE`, `AIL_ASK_AGI`, `AIL_REDIS_CACHE`

## Storage

In-memory first (same pattern as FRE/FAA). Optional Redis cache. Optional Supabase migration for durable ledger/dossier tables.
