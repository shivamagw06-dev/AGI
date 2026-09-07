# Phase 1 — Evidence-First Execution Governance

**Architecture:** v1.0.1 LOCKED · soft-wire only · no new top-level engines

Transforms Ask AGI research answers from “AI that answers” into
**evidence-governed institutional reasoning**.

## Pipeline

```text
Question
  → Classification
  → Entity Resolution
  → Evidence Contract
  → Framework Selection
  → Evidence Validation
  → Framework Execution (structured outputs only)
  → Committee (framework outputs only)
  → Editorial (explain only; cannot invent)
  → Immutable Telemetry
```

Education questions (`What is ROIC?`) bypass evidence/frameworks/committee
and route to Academy Books.

## Soft helpers (not engines)

| Module | Role |
|--------|------|
| `institutional_reasoning/evidence_contracts.py` | Question types, contracts, entity map, forbidden claims |
| `institutional_reasoning/evidence_validation.py` | Entity match, placeholder, freshness, coverage |
| `institutional_reasoning/execution_governance.py` | Pipeline + committee + editorial enforce |
| `institutional_reasoning/telemetry_sink.py` | Append-only Supabase / disk / memory sink |

## Telemetry

Migration: `supabase/migrations/20260727230000_framework_execution_runs.sql`

Table `framework_execution_runs` is **append-only** (UPDATE/DELETE blocked by trigger).

## Acceptance

`intelligence-engine/tests/test_phase1_acceptance.py`

1. Missing historical PE → cannot determine (not “expensive”)
2. Wrong entity (`IS` vs `NIFTYIT`) → blocked
3. Placeholder `0` → rejected
4. Education → Academy path
5. Framework disagreement → committee explains both sides

## Ops

1. Redeploy Intelligence Engine from `main`
2. Run the migration in Supabase (or rely on disk fallback under `KIP_DATA_DIR`)
3. Ensure IE has `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` for remote telemetry
