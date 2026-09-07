# Institutional Research Execution Package (IREP) V1

**RQ1 Sprint 10 — final RQ1 output.** Soft-wired Intent Intelligence package. Not a top-level intelligence layer.

## Primary question

> What institutional research package should be executed?

## Law

No downstream component independently interprets the user's question. IREP is immutable once generated. It is the contract between planning and reasoning.

## Package

- `package_builder/` — assembles RQ1 Sprints 1–9 into one canonical package
- `package_validator/` — completeness + consistency
- `package_memory/` / `package_audit/` / `package_export/` / `package_version/`
- `research_contract/` — internal Research Contract before execution
- `diagnostics/`

## APIs

`/v1/research-execution/{health,constitution,dashboard,quality-gates,build,plan,enrich,export,diagnostics}`

## Admin

`/admin/research-execution`
