# Institutional Company Intelligence (ICI) — AGIB v2.0 Sprint 1

## Role

Soft Knowledge Factory package that deepens **qualitative business intelligence** for listed Indian companies.

**Not** a reasoning engine. **Not** ratio enrichment. **Not** a governance/planner change.

## Freeze locks

Do not modify: Phase 1–7 Reasoning, KF architecture, Universe Intelligence architecture, Decision Quality, governance, committees, planner, evidence contracts, framework execution, learning engine.

## Package

```
knowledge_factory/company_intelligence/
  docs/ collectors/ validators/ objects/ producers/ dashboard/ apis/ tests/
```

Soft-wire only.

## Naming note

Universe Intelligence uses **ICI = Institutional Coverage Index**.  
This package is **Institutional Company Intelligence** (`institutional-company-intelligence-v2.0.0`). Dashboards label them distinctly.

## Sprint split

- **1A:** identity, business model, products, segments, customers, management, ownership  
- **1B:** capital allocation, competition, business quality (existing evidence only), business risk, timeline, knowledge links, APIs, dashboard, quality gates  

Both land in this package in one PR; modules are tagged in the object.

## Coverage levels

0 Discovered → 1 Identity → 2 Business Model → 3 Products & Segments → 4 Management & Ownership → 5 Competition & Risks → 6 Timeline → 7 Institutional Company Intelligence (COMPLETE)

## Provenance

Every field: source, retrieved_at, validated_at, collector, confidence, derived_from, version.

Unavailable → explicit `UNKNOWN` (never fabricated).

## APIs (read-only)

- `/v1/company-intelligence/{ticker}`
- `/v1/company-intelligence/dashboard`
- `/v1/company-intelligence/coverage`
- `/v1/company-intelligence/quality`
- `/v1/company-intelligence/search`
