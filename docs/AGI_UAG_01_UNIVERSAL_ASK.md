# UAG-01 — Universal Ask AGI Orchestrator

Phase 5.1 — One conversational interface over existing AGI objects.

## Mission

UAG-01 **owns orchestration, not reasoning**.

It retrieves, assembles, validates, and explains. It never generates investment decisions.

## Architecture

```text
User → Universal Ask AGI → Intent → Query Planner → Object Registry
      → Providers (Decision / Risk / Policy / Committee / …)
      → Evidence Assembler → Institutional Response
```

## Invariant

Stateless with respect to business state:

- Company decisions remain owned by IDS
- Portfolio risk by PRE-01
- Policy by PCE-01
- Portfolio decisions by CIO-01
- Committee resolutions by ICE-01

UAG creates an execution plan, invokes providers, assembles a response, and finishes.

## Package

`intelligence-engine/institutional_orchestrator/`

## Objects

- `InstitutionalQuery` — intent, entities, planners, execution plan
- `InstitutionalResponse` — direct answer, why, evidence, lineage, confidence

## Object Registry

Engines register capabilities (`object_type`, route phrases, provider, retrieve). The router discovers — no hardcoded engine selection.

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_orchestrator \
  --query "Why reduce HDFCBANK?"
```

## API

- `GET /v1/orchestrator/health`
- `POST /v1/ask`
- `POST /v1/ask/stream`
- `GET /v1/query/{id}`

BFF: `/api/intelligence/ask`, `/api/intelligence/orchestrator/health`, …

## Quality gates

Reject if: no execution plan, no supporting objects, unresolved entity ambiguity, missing evidence for factual claims, or orchestrator attempts to generate recommendations.

## Success criteria

- One institutional entry point
- Deterministic routing via registry
- Every answer backed by evidence lineage
- No LLM-generated investment recommendations
- Fully explainable execution plans
