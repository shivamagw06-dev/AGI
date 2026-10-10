# Company Analysis Engine V1

**Architecture status:** v1.0.1 LOCKED  
**Role:** Institutional analysis layer — apply Academy knowledge to companies with live evidence.  
**Not:** recommendation engine · market-data engine · LLM · Context Assembly Engine (`app/cae`)

## Naming

Context Assembly already occupies **`CAE` / `cae`** in this codebase.  
This programme uses package `company_analysis` and master flag **`COMPANY_ANALYSIS`**.  
Subflags match the brief: `CAE_FINANCIAL`, `CAE_SECTOR`, `CAE_BUSINESS`, `CAE_VALUATION`, `CAE_INVESTMENT_THESIS`.

## Soft-wire path

Ask AGI → CID → KF → Academy → **Company Analysis** → IRP → Institutional Answer

## Consumes only

CID · Knowledge Foundation · Academy · FIE/dossier financials · LEO · DVC · Sector Academy/SIF · Market events · Research/Prediction history · IRP evidence packs  
Never raw provider payloads.

## Flags

`COMPANY_ANALYSIS`, `CAE_FINANCIAL`, `CAE_SECTOR`, `CAE_BUSINESS`, `CAE_VALUATION`, `CAE_INVESTMENT_THESIS`

## APIs

- `GET /v1/company-analysis/health`
- `GET /v1/company-analysis/dashboard`
- `GET /v1/company-analysis/quality-gates`
- `GET /v1/company-analysis/report/{ticker}`
- `POST /v1/company-analysis/analyse`

## Admin

`/admin/company-analysis`
