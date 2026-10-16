# Institutional Alternative Data Intelligence (IADI)

AGIB v2.0 Sprint 6 — soft Knowledge Factory layer.

## Role

Teach AGIB to observe **high-signal real-economy activity** that often precedes company earnings.

- Not a prediction engine
- Not a reasoning change
- Not a planner / committee

## Phase 1 scope (intentional)

Start with **10 high-signal datasets** that are published consistently and link well to listed companies:

1. UPI transactions (NPCI)
2. Electricity demand (Grid India / POSOCO)
3. IIP manufacturing (MOSPI) — public substitute for licensed PMI
4. Railway freight (Indian Railways)
5. Port cargo (Ministry / IPA)
6. Vehicle registrations (VAHAN aggregates)
7. Domestic air passengers (DGCA)
8. Bank credit growth (RBI)
9. Rainfall / monsoon (IMD)
10. GST collections (GSTN published aggregates)

Broader domains (full payments stack, property, telecom, PMI, etc.) remain **Phase-2 extensible shells**.

## Package

```
knowledge_factory/alternative_data_intelligence/
  docs/ collectors/ validators/ objects/ producers/
  registry/ trends/ links/ fixtures/ dashboards/ apis/ tests/
```

## APIs (read-only)

Prefix: `/v1/alternative-data`

- `/dashboard`
- `/search`
- `/dataset/{name}`
- `/company/{ticker}`
- `/industry/{industry}`
- `/trends`
- `/replay`

## Freeze

All prior layers including Economic Relationship Intelligence: **frozen**. Soft-wire only.

## Never invent

No fabricated observations. No unsupported interpolation. UNKNOWN when unavailable. Company/industry links only from supported registry mappings + soft IERI reads.
