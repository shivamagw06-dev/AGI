# RQ1 Sprint 2 — Entity Resolution Engine (ERE) V1

**Primary question:** What is the canonical institutional entity?

**Law:** Never guess. No analyst, API, or intelligence layer may execute before entity resolution succeeds.

## Source of truth

```
User Question → ERE → Institutional Knowledge Graph → Canonical Entity + Relationships
```

ERE registry is a soft fallback when IKG coverage is sparse. Ambiguous stems (`HDFC`, `Tata`, `ICICI`) always clarify unless conversation context uniquely resolves them.

## API

| Method | Path |
|---|---|
| GET | `/v1/entity-resolution/health` |
| GET | `/v1/entity-resolution/constitution` |
| GET | `/v1/entity-resolution/dashboard` |
| GET | `/v1/entity-resolution/quality-gates` |
| POST | `/v1/entity-resolution/resolve` |
| POST | `/v1/entity-resolution/diagnostics` |

## Admin

`/admin/entity-resolution`
