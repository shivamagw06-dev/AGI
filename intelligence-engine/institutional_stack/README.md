# Institutional Intelligence Stack (IIS)

Soft integration layer — **not a new engine**.

Wires FIL → FDI → MII → EIL → PIL into Company Analysis, Institutional Analysts, Ask AGI, IRS, Mission Control, and the website admin/API gateway.

## Pipeline

```text
Official Filings → FIL → FDI → MII → EIL → PIL → Analysts → IC → CIO → RW → ACS → IRS → Production
```

## APIs

- `GET /v1/institutional-stack/health`
- `GET /v1/institutional-stack/dashboard`
- `GET /v1/institutional-stack/company/{ticker}`
- `POST /v1/institutional-stack/analyse`
- `POST /v1/institutional-stack/ingest` — filing ingest + auto FDI/MII chain
- `POST /v1/institutional-stack/bootstrap` — seed corpus + refresh defaults
- `GET /v1/admin/institutional-stack`

## Flag

`INSTITUTIONAL_STACK=true` (default on)
