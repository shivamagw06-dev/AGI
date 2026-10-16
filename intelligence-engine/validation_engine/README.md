# Institutional Validation & Clarification Engine (IVCE) V1

**RQ1 Sprint 9** — soft-wired Intent Intelligence package. Not a top-level intelligence layer.

## Primary question

> Is this request sufficiently understood and supported to begin institutional research?

## Law

No institutional research begins until the request has passed all validation gates.

## Package

- Question / entity / ambiguity / evidence / blueprint / routing / policy validators
- Clarification engine
- Readiness gate (`READY` / `READY_WITH_WARNINGS` / `CLARIFICATION_REQUIRED` / `BLOCKED`)
- **Research Readiness Memo** for downstream components

## APIs

`/v1/validation-engine/{health,constitution,dashboard,quality-gates,validate,plan,enrich,diagnostics}`

## Admin

`/admin/validation-engine`
