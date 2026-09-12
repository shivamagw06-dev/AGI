# Causal Intelligence Graph (CIG) V1

Institutional market relationship engine. Soft intelligence layer — **not** an engine redesign.

## Primary question

**Why did this happen?**

## Architecture status

`v1.0.1 LOCKED`

## Position

```
FIL → FDI → MII → ACI → EIL → PIL → CIG → Analysts → Committee → PIO → CIO → RW → ACS → IRS
```

## Flag

`CAUSAL_INTELLIGENCE=true`

## API

- `GET /v1/causal-intelligence/health`
- `GET /v1/causal-intelligence/dashboard`
- `GET /v1/causal-intelligence/company/{ticker}`
- `GET /v1/causal-intelligence/event/{event}`
- `POST /v1/causal-intelligence/analyse`
- `GET /v1/causal-intelligence/graph`
- `GET /admin/causal-intelligence`

## Constraints

No redesign of FIL, FDI, MII, ACI, EIL, PIL, PIO, analysts, committee, CIO, research writer, ACS, IRS, providers, or UI engines.
