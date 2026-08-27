# AGIB Architecture Freeze (v3)

**Status:** LOCKED after Institutional Decision Engine V2  
**Architecture:** v1.0.1 LOCKED

## Final top-level pipeline

```text
Official Data Providers
        │
        ▼
FIL  →  FDI  →  MII  →  ACI
        │
        ▼
EIL  →  PIL  →  CIG  →  IKG
        │
        ▼
FIE  →  ILM  →  SSL
        │
        ▼
Institutional Analysts
        │
        ▼
Investment Committee
        │
        ▼
Portfolio Intelligence Office
        │
        ▼
Institutional Decision Engine V2
        │
        ▼
CIO → Research Writer → ACS → IRS → Production
```

## Freeze rule

**No new top-level intelligence layers after IDE V2.**

Future releases improve:

- evidence quality and coverage
- data coverage
- reasoning quality
- analyst intelligence / depth
- forecast and decision calibration
- institutional learning

—not architectural complexity.

## Freeze review checklist

For each top-level module, confirm:

1. One clear responsibility
2. No duplicate responsibility across modules
3. Every output has a clear owner
4. Every decision is audit-traceable
5. Every claim is evidence-backed
6. Forecasts are calibrated over time (FIE + ILM hooks)
7. Recommendations are reproducible from stored inputs (IDE V2 audit)

Machine-readable answers live in `decision_engine_v2.schema.FREEZE_REVIEW` and
`GET /v1/decision-engine-v2/freeze-review`.
