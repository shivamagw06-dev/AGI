# Institutional Economic Relationship Intelligence (IERI)

AGIB v2.0 Sprint 5 — soft Knowledge Factory layer.

## Role

Structured institutional knowledge describing how the Indian economy is connected.

- Not a reasoning engine
- Not a graph-database product
- Not a planner

The **Economic Relationship Graph** is an implementation detail. The product is evidence-backed economic relationship knowledge with provenance, point-in-time integrity, and an **economic semantics** taxonomy.

## Economic semantics

Every relationship is classified as one of:

| Semantics | Examples |
|-----------|----------|
| structural | supplier, subsidiary, competitor, JV |
| financial | ownership, funding, credit exposure |
| policy | RBI, GST, PLI, duties, budget |
| market | commodity, pricing, demand, rate sensitivity |
| operational | logistics, power, ports, labour |
| behavioural | substitutes, complements |

## Package

```
knowledge_factory/economic_relationship_intelligence/
  docs/ collectors/ validators/ registry/ graph/
  relationship_objects/ company_links/ industry_links/
  commodity_links/ government_links/ macro_links/
  transmission/ dashboards/ apis/ fixtures/ tests/
```

## APIs (read-only)

Prefix: `/v1/relationship`

- `/dashboard` — Morning Board
- `/company/{ticker}`
- `/industry/{industry}`
- `/commodity/{commodity}`
- `/policy/{policy}`
- `/macro/{macro}`
- `/network/{entity}`
- `/path`
- `/search`
- `/replay?as_of=`
- `/shock/{entity}` — beneficiaries / losers from stored edges

## Freeze

Phase 1–7, governance, committees, Decision Quality, Universe / Company / Corporate Events / Government / Industry intelligence: **frozen**. Soft-wire only.

## Never invent

Missing relationships stay absent / UNKNOWN. No autonomous inference of unsupported edges.
