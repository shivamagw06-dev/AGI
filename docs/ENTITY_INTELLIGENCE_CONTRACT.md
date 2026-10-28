# Entity Intelligence & Verified Entity Contract (P0)

## Law

> **Never answer for the wrong entity.**

Entity Intelligence is the single authority for company identification and sits **before** Knowledge Unification / Ask planners.

## Failure that motivated this

```
User: Air India
AGI:  BHARTIARTL   ← FORBIDDEN
```

Investment / Business / Industry engines may have reasoned correctly — on the wrong company.

## Contract states

Every Ask request must resolve to exactly one of:

- `verified_entity`
- `verified_concept`
- `verified_industry`
- `verified_macro`
- `clarification_required`
- `unsupported_entity`

## Confidence

| Score | Action |
|------:|--------|
| ≥0.95 | Verified — planner may run (if coverage allows) |
| 0.80–0.95 | Clarification |
| <0.80 | Do not execute planner |

Private / insufficient-coverage entities (e.g. **Air India**) resolve as `verified_entity` with `allow_planner=False` and an honest coverage message — never a CapIQ substitute.

## Commands

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_entity_intelligence_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_entity_golden_50.py
```

## Release gate

- Entity Acceptance ≥400Q → **100%**
- Entity Golden 50 → **100%**
- Wrong entity bindings → **0**
- Substitutions → **0**
