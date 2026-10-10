# Institutional Knowledge Graph (IKG) V1

Universal institutional knowledge layer. Soft intelligence layer — **not** an engine redesign.

## Primary question

**What is connected?**

## Architecture status

`v1.0.1 LOCKED`

## Position

```
FIL → FDI → MII → ACI → EIL → PIL → CIG → IKG → Analysts → IC → PIO → FIE → CIO → RW → ACS → IRS
```

## Flag

`KNOWLEDGE_GRAPH=true`

## Rules

- Every relationship has evidence
- Every node has one canonical identity
- No duplicate entities
- Historical edges preserved
- Unsupported edges rejected

## API

- `GET /v1/knowledge-graph/entity/{id}`
- `GET /v1/knowledge-graph/company/{ticker}`
- `GET /v1/knowledge-graph/relationships/{id}`
- `POST /v1/knowledge-graph/query`
- `GET /v1/knowledge-graph/path`
- `GET /admin/knowledge-graph`
