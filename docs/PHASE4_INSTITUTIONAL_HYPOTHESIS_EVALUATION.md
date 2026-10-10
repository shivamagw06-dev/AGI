# AGI Phase 4 Sprint 4.3 — Institutional Hypothesis Evaluation Engine (IHE)

```text
COMPANY: AGI
MODULE: IHE
VERSION: institutional-hypothesis-evaluation-v1.0.0
PROFILE: ihe-evaluation-profile-v1.0.0
STATUS: soft-wired after IHG / before Reasoning
```

## Purpose

Decide **which hypothesis best explains the evidence**, while preserving
uncertainty, conflicts, and missing-evidence gaps.

```text
IEW → IHG → IHE → Reasoning → ICE
```

Not an LLM. Not a contradiction detector alone. Not a reasoning replacement.

## Evaluation dimensions

Support · Conflict (retained) · Coverage · Historical consistency ·
Framework consistency · Missing evidence · Alternative strength ·
Explanatory power

## Outcomes (no forced winner)

`Preferred` · `Plausible` · `Rejected` · `Indeterminate`

Balanced evidence → multiple viable explanations.

## LangSmith

- `hypothesis_evaluation`
- `hypothesis_evaluation.hypothesis` (per hypothesis scores + missing evidence)

## APIs

`/v1/hypothesis-evaluation/{health,dashboard,evaluate,report,ranking,telemetry,history}`

## Frozen upstream

IEW v1.0.0 and IHG v1.0.0 remain frozen — IHE consumes them only.
