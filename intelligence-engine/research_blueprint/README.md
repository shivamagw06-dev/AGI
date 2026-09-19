# Dynamic Research Blueprint Engine (DRBE) V1

**RQ1 Sprint 8** — soft-wired Intent Intelligence package. Not a top-level intelligence layer.

## Primary question

> What is the optimal institutional report structure?

## Law

The blueprint is finalised before research begins. Every question deserves a different report.

## Package

- `blueprint_registry/` — report types, mandatory/optional sections, style
- `report_selector/` — question → report type
- `section_generator/` / `section_priority/` / `dynamic_layout/`
- `ownership_engine/` — section → analyst owner
- `quality_rules/` / `rendering_contract/` / `report_policy/`
- `assignment_book/` — Research Assignment Book (missions before reasoning)
- `diagnostics/`

## APIs

`/v1/research-blueprint/{health,constitution,dashboard,quality-gates,plan,enrich,diagnostics}`

## Admin

`/admin/blueprint-engine`
