# Institutional Market Expectations Intelligence (IMEI)

AGIB v2.0 Sprint 7 — soft Knowledge Factory layer.

## Principle

> Markets price expectations, not reality.

Prior sprints taught AGIB **reality**. This sprint teaches **expectations**, completing the institutional knowledge stack.

## What this is not

- Not broker report ingestion
- Not recommendation aggregation
- Not sentiment analysis
- Not a prediction engine

## Two-phase delivery

### Phase 1 (this sprint)

Public, auditable sources only:

1. Company-issued guidance
2. Company earnings releases / actuals
3. Exchange disclosures
4. Investor presentations
5. AGIB timestamped internal forecasts

### Phase 2 (optional, modular)

`collectors/consensus_licensed.py` — inactive unless `AGIB_LICENSED_CONSENSUS_PROVIDER` is set. Never assumes proprietary street consensus. Unavailable → `UNKNOWN`.

## Package

```
knowledge_factory/market_expectations_intelligence/
  docs/ collectors/ validators/ registry/ objects/
  expectations/ revisions/ surprises/ narratives/
  dashboards/ apis/ fixtures/ tests/
```

## APIs (read-only)

Prefix: `/v1/expectations`

- `/dashboard`
- `/company/{ticker}`
- `/revisions`
- `/surprises`
- `/narratives`
- `/search`
- `/replay`
- `/gap/{ticker}`

## Freeze

All prior layers including Alternative Data Intelligence: **frozen**. Soft-wire only.
