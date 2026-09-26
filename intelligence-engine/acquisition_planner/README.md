# Institutional Acquisition & API Planning Engine (IAPE) V1

**RQ1 Sprint 7** — soft-wired Intent Intelligence package. Not a top-level intelligence layer.

## Primary question

> What evidence must be acquired to answer this question?

## Law

Every API call must have a reason. Acquire only the minimum evidence required for institutional quality.

## Package

- `api_registry/` — providers (purpose, types, coverage, latency, freshness, authority, cost, fallbacks)
- `evidence_requirements/` — evidence plan from research objective
- `provider_selector/` — primary + fallback by authority / freshness / latency
- `cache_manager/` — FIL / PIL / IKG / EIL / ILM reuse first
- `redundancy_detector/` — zero duplicate fetches
- `freshness_engine/` — live / intraday / daily / quarterly / existing knowledge
- `evidence_budget/` — max runtime, max API calls, target confidence, min authority
- `cost_engine/` / `quality_engine/` / `confidence_engine/` / `fallback_engine/`
- `acquisition_plan/` — composed plan object
- `diagnostics/` — explain acquire / reuse / skip

## APIs

`/v1/acquisition-planner/{health,constitution,dashboard,quality-gates,plan,enrich,diagnostics}`

## Admin

`/admin/acquisition-planner`
