# ICE-01 — Investment Committee Engine

Phase 4.5 — Institutional decision governance for the Investment Office.

## Mission

Portfolio decisions become committee decisions.

```text
PKG → PRE → PCE → CIO
        ↓
Investment Committee
        ↓
Committee Resolution
        ↓
Execution Queue (future)
```

The committee is **not** another decision engine. It is a **governance engine**.

## Architecture

```text
Portfolio Graph
      ↓
Portfolio Risk
      ↓
Policy Assessment
      ↓
Portfolio Decision
      ↓
Investment Committee Engine
      ↓
Committee Resolution
      ↓
Investment Office
```

## Invariant

ICE-01 **never alters** company decisions, portfolio risk, or policy assessments. It references CIO-01 outputs and records the organization's governance response.

## Package

`intelligence-engine/institutional_committee/`

## Object

`InstitutionalCommitteeResolution` — immutable, versioned.

Statuses: Pending Review · Approved · Approved with Conditions · Rejected · Deferred · Escalated

## Voting desks (deterministic)

Risk · Policy · Allocation — structured outcomes, not people simulation.

## Lineage

```text
Committee → Resolution → Portfolio Decision → Policy Assessment → Portfolio Risk → Evidence
```

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_committee --portfolio default
```

## API

- `GET /v1/committee-engine/health`
- `POST /v1/committee/review`
- `GET /v1/committee/pending`
- `GET /v1/committee/resolution/{resolution_id}`
- `GET /v1/committee/portfolio/{portfolio_id}`

BFF: `/api/intelligence/committee/*`

> Note: Legacy IC deliberation routes under `/v1/committee/health|dashboard|…` remain separate. ICE resolution fetch uses `/committee/resolution/{id}` to avoid path collisions.

## Quality gates

Reject if missing portfolio decision, policy assessment, risk assessment, rationale, outcome, votes, or diagnostics.

## Success criteria

- Resolutions are first-class immutable objects
- Portfolio decisions remain unchanged (referenced)
- Approvals/rejections are explainable and auditable
- Action items and follow-ups generated automatically
- Full lineage to evidence
