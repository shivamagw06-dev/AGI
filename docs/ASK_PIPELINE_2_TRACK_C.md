# AGIB v3.4 Track C — Institutional Framework Selection Engine (IFSE)

## Goal

Before reasoning starts, determine **which institutional analytical framework(s)** apply.

```text
Question → Intent → Evidence → Answer Assembly → Framework Selection → Existing Reasoning → Narrative
```

## Package

`intelligence-engine/framework_selection/`

| Area | Role |
|------|------|
| `registry/` | Phase-1 frameworks + metadata |
| `mappings/` | Sector / company / question overlays |
| `rules/` | Forbidden frameworks + composition rules |
| `selector/` | Deterministic multi-framework composition |
| `confidence/` | Selection confidence |
| `validation/` | Quality gates |
| `replay/` | `available_from <= as_of` |
| `explanation/` | Framework Explanation Object |
| `dashboard/` | Usage / accuracy / wrong-framework rate |
| `production.py` | Facade + `/v1/framework-selection/*` |

## Soft-wires

- Ask Pipeline — after Answer Assembly, before planner/reasoning; packs overlay + `institutional_answer.framework_selection`
- Research Office — `framework_used`, `framework_confidence`, `framework_version` on publications
- Mission Control — IFSE board soft-read
- API — `/framework-selection/{health,dashboard,registry,select,history,...}`

## Frozen

KF, governance internals, committees, planner logic, reasoning engine — unchanged.

## Framework Explanation Object

Internally recorded on every selection (not shown by default):

- Selected frameworks with roles (primary / secondary / supporting)
- Reason (sector + intent + exclusions)
- Confidence
- Evidence required

## Exit discipline

Re-run the same 25-question CIO benchmark after merge. Merge only if score improves or stays neutral without regressions. Track D (narrative) is next.
