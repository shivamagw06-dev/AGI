# PCE-01 — Institutional Policy & Constraint Engine

Phase 4.4 — Institutional governance for the Investment Office.

## Mission

The CIO can recommend allocations. PCE-01 answers first:

> **"Is this portfolio allowed to do that?"**

Risk describes. Policy governs. Decision acts.

## Architecture

```text
Portfolio Graph (PKG-01)
      ↓
Portfolio Risk (PRE-01)
      ↓
Policy & Constraint Engine (PCE-01)
      ↓
InstitutionalPolicyAssessment
      ↓
Portfolio Decision (CIO-01)
      ↓
Investment Office
```

## Package

`intelligence-engine/institutional_policy/`

## Object

`InstitutionalPolicyAssessment` — immutable, versioned.

Fields: overall status, violations, warnings, passed/failed constraints, mandate, compliance score, required actions, diagnostics.

## Constraint categories

Position · Sector · Cash · Diversification · Liquidity · Risk

## Policy profiles

`family_office` · `balanced` · `conservative` · `growth` · `pms` · `mutual_fund` · `custom`

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_policy --portfolio default --policy family_office
```

## API

- `GET /v1/policy/health`
- `POST /v1/policy/check`
- `GET /v1/policy/{portfolio}`

BFF: `/api/intelligence/policy/*`

## CIO integration

CIO-01 consumes PCE-01. Policy breaches outrank heuristic risk rules, e.g.:

```text
Reduce Concentration
Reason: Policy Violation — Maximum Holding Exceeded
```

## Out of scope

Optimisation, soft-constraint solvers, regulatory filing automation, multi-account netting.

## Success criteria

- Policy is a first-class object
- CIO consumes policy (no duplicated constraint logic)
- Deterministic evaluation
- Explainable, actionable violations
- Immutable assessments
