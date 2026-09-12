# CID v1.0 Validation

## Mission

Permanent institutional memory for every tracked company. LEO updates dossiers from verified evidence; Ask AGI starts company analysis from the dossier.

## HDFC Bank

| Check | Result |
|---|---|
| Dossier created | Yes (`HDFCBANK`) |
| LEO ingest → timeline | Yes (50+ events) |
| Documents | Annual, quarterly, presentations, transcripts |
| Announcements | NSE/BSE streams |
| SIF attached | `banks` + priority KPIs (NIM, CASA, …) |
| Finance Academy linked | Active concepts present |
| Coverage score / grade | Computed (Partial/Research until live market+valuation) |
| Ask AGI uses dossier | `SearchView.company_dossier` + CID hints in why |

## Tracked universe quality gates

HDFCBANK, INFY, RELIANCE, ULTRACEMCO, ASIANPAINT, TATASTEEL, SUNPHARMA, POWERGRID

- Dossiers created
- Evidence continuously updates (timeline never shrinks on re-ingest)
- Coverage calculated
- SIF attached per sector
- Academy linked
- LEO updates CID after every package

## Admin / API

- `/admin/company-dossiers`
- `/v1/company-dossier/{ticker}` (+ timeline, coverage, valuation, risk, forecast, documents)

## Architecture

No new engine. CID is additive permanent memory on top of LEO. v1.0.1 LOCKED engines unchanged.
