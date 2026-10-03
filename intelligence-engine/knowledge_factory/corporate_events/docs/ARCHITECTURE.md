# Institutional Corporate Event Intelligence (ICEI) — AGIB v2.0 Sprint 2

## Role

Soft Knowledge Factory package that maintains an **immutable, point-in-time corporate event timeline** for listed Indian companies.

Financial statements say *what happened*. Corporate events say *why it happened*.

**Not** a reasoning engine. **Not** a planner. **Not** governance.

## Dependency

```
Company Intelligence (Sprint 1)
        ↓
Corporate Event Intelligence (Sprint 2)
        ↓
Government & Regulatory Intelligence (later)
```

## Freeze locks

Do not modify: Phase 1–7 Reasoning, KF architecture, Company Intelligence architecture, Universe Intelligence, Decision Quality, governance, committees, planner, evidence contracts, learning.

## Never invent events

Events come only from:
1. Curated ICEI seeds
2. Company Intelligence timeline soft-reads
3. Historical Depth timeline / corporate-action soft-reads

## Point-in-time

Every event stores `announcement_date`, `available_from`, `effective_date`.

Replay rule: `available_from <= as_of`. Future leakage is forbidden.

## APIs (read-only)

- `/v1/corporate-events/{ticker}`
- `/v1/corporate-events/search`
- `/v1/company-timeline/{ticker}`
- `/v1/corporate-events/dashboard`
- `/v1/events/today`
- `/v1/events/critical`
