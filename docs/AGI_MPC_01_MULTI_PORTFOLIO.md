# MPC-01 — Multi-Portfolio & Client Platform

Phase 5.5 — From institutional research platform to institutional operating system.

## Core principle

> **Intelligence is global. Portfolios, mandates, permissions, and workflows are local.**

MPC owns **tenancy and workflow**. Intelligence engines remain unchanged.

## Architecture

```text
                     AGIB Platform
                           │
                           ▼
             Multi-Portfolio Platform (MPC)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Portfolio Manager     Client Manager     Team Manager
                           │
                           ▼
                 Workspace Resolver
                           │
                           ▼
                  Intelligence Layer
```

## Package

`intelligence-engine/institutional_multi_portfolio/`

## Core objects

### InstitutionalExecutionContext

Immutable context that flows through orchestration — never hidden session state:

```python
InstitutionalExecutionContext(
    workspace_id,
    portfolio_id,
    client_id,
    mandate_id,
    role_id,
)
```

UAG, RW, PUB, CIO, and PCE receive this explicitly. Domain engines may ignore unused fields.

### InstitutionalPortfolioWorkspace / InstitutionalClient

Local tenancy objects that **reference** shared intelligence — they do not duplicate it.

## Mandate Engine

```text
Portfolio → Mandate → Policy Profile (PCE-01) → Risk Limits → Committee Workflow
```

MPC maps mandates to PCE profiles. PCE remains system of record for policy evaluation.

## Permissions

Separated from data. Roles affect workflow, not intelligence. Engines must not check permissions directly.

## Ask AGI

Context changes the response scope, not company truth:

> Should Portfolio Alpha increase HDFCBANK?

```text
Portfolio Context → Mandate → Policy → Portfolio Decision → Company Decision → Evidence
```

## API

- `GET/POST /v1/portfolios`
- `GET/POST /v1/clients`
- `GET /v1/workspaces/{id}` · `POST /v1/workspaces/resolve`
- `POST /v1/permissions`
- `POST /v1/platform/context` · `POST /v1/platform/ask`

## Surfaces

- Mission Control **Platform Operations Center**
- Research Workspace portfolio switcher + mandate/context strip
- Intelligence Map `MPC01`

## Success criteria

- One intelligence layer serves many portfolios
- Mandates and permissions isolated from analysis
- Ask becomes context-aware without changing company truth
- Publications support portfolio/client-scoped distribution of the same object
- Intelligence objects remain globally authoritative
