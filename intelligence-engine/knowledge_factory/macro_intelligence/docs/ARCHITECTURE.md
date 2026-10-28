# Sprint 6 — Institutional Macro Intelligence (IMI)

## Stance

Knowledge Factory enrichment **only**. Reasoning Architecture Frozen v1.0.

- Do **not** modify Phases 1–7
- Do **not** modify Historical Depth or Sector Intelligence implementations
- Do **not** create new reasoning engines, planners, committees, or portfolio logic
- Macro is institutional knowledge consumed by existing producers

## Architecture

```
Knowledge Factory
  → Macro Collectors (fixtures / series)
  → Macro Validators
  → Macro Derived Producers
  → Macro Knowledge Objects + DNA
  → Macro Playbooks + Decision Matrix
  → Historical Macro Objects (PIT)
  → Macro Evidence Packs
  → Existing Evidence Producers
  → Existing AGIB Phases 1–7 (untouched)
```

## Point-in-time

All historical queries filter `available_from <= as_of`. Missing history returns transparent insufficiency — never fabricate.

## Macro Decision Matrix

Regime → preferred / de-emphasised frameworks + confidence adjustments. Knowledge only for existing framework-selection consumers.

## North Star KPI

`institutional_macro_intelligence_coverage`
