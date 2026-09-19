# Business Intelligence

Two layers:

1. **FIRE-03** — disclosure evidence extraction (this package root)
2. **Phase 3.0 Foundation** — deterministic business reasoning (`foundation/`)

Phase 3.0 Ask wiring is **disabled** until the BI Acceptance Test ≥95%.
See [`foundation/PHASE3_NOTES.md`](foundation/PHASE3_NOTES.md).

---

# FIRE-03 — Business & Management Intelligence

Evidence extraction engine over official company disclosures (IDI).

**Spec:** [`docs/FIRE_03_BUSINESS_MANAGEMENT_INTELLIGENCE.md`](../../docs/FIRE_03_BUSINESS_MANAGEMENT_INTELLIGENCE.md)

## Rules

- Official company documents only (annual reports, presentations, transcripts, governance, risk disclosures)
- Structured `BusinessFact` objects with page / section / document / period / confidence
- Soft FKB glossary links — never duplicate definitions
- Never mutates FSE / Warehouse / IDI / FIRE-01 / FIRE-02
- Never BUY / SELL / valuation / forecast / sentiment / LLM summaries

## CLI

```bash
export PYTHONPATH=.
python -m business_intelligence --health
python -m business_intelligence --company TCS
python -m business_intelligence --segments TCS
python -m business_intelligence --strategy TCS
python -m business_intelligence --risks TCS
python -m business_intelligence --guidance TCS
```

## API

- `GET /v1/business-intelligence/health`
- `GET /v1/business-intelligence/dashboard`
- `GET /v1/business-intelligence/company/{ticker}`
- `GET /v1/business-intelligence/company/{ticker}/segments`
- `GET /v1/business-intelligence/company/{ticker}/strategy`
- `GET /v1/business-intelligence/company/{ticker}/risks`
- `GET /v1/business-intelligence/company/{ticker}/guidance`
