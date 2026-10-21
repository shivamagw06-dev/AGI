# CCI-01 — Cross-Company Intelligence

Phase 5.3 — Market intelligence via relationship reasoning over KG-01.

## Mission

Transform AGI from a company-centric research platform into a **market intelligence platform**.

| Before | After |
|--------|-------|
| *What do we think about HDFC Bank?* | *How does HDFC Bank affect everything else?* |

## Critical architectural rule

**CCI-01 does not build another graph.**

- **KG-01** owns the graph (system of record)
- **CCI-01** owns traversal, relationship discovery, similarity, clustering, and dependency propagation

## Architecture

```text
                    Universal Ask AGI
                           │
                           ▼
                Cross-Company Intelligence
                           │
                 Relationship Planner
                           │
                           ▼
                 Knowledge Graph (KG-01)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Company Network      Sector Network    Macro Network
                           │
                           ▼
                  Relationship Engine
                           │
                           ▼
               Institutional Intelligence
```

## Package

`intelligence-engine/institutional_cross_company/`

## Core object

```python
InstitutionalRelationship(
    relationship_id,
    source_entity,
    target_entity,
    relationship_type,
    strength,
    confidence,
    evidence=[],
    propagation_path=[],
    diagnostics=None,
)
```

Immutable. Versioned. Every relationship links back to supporting evidence.

## Relationship provider registry

Like UAG-01's object registry — CCI orchestrates providers; new relationship types do not require core engine rewrites.

```python
register_relationship_provider(
    relationship_type="competitor",
    provider="competitor_engine",
)

register_relationship_provider(
    relationship_type="macro",
    provider="macro_dependency_engine",
)
```

## Engines

| Engine | Role |
|--------|------|
| Relationship | Discover competitors, sector, macro, portfolio links |
| Traversal | Walk relationship neighborhoods; soft-ref KG-01 |
| Propagation | Dependency paths (not forecasts) |
| Similarity | Ranked similar companies |
| Clustering | Private Banks, IT Services, Auto OEMs, … |
| Impact | Driver → companies → portfolio → risk/committee consumers |

## Propagation (not prediction)

```text
RBI cuts rates → Banking Sector → NIMs → Company Decisions → Portfolio Decisions
```

CCI emits the dependency path. Domain engines remain systems of record for decisions.

## API

- `GET /v1/relationships/company/{ticker}`
- `GET /v1/relationships/sector/{sector}`
- `GET /v1/relationships/macro/{driver}`
- `POST /v1/relationships/query`

## Surfaces

- Research Workspace **Relationship Map** tab
- Mission Control **Relationship Center**
- Universal Ask routes `Relationship` object type via registry
- Intelligence Map `CCI01`

## Invariants

- `owns_graph: false`
- `graph_system_of_record: KG-01`
- `predictive: false`
- `generates_recommendations: false`
- Reject relationships without evidence, below confidence, circular without justification, or duplicates

## Success criteria

- Cross-company relationships are first-class objects
- KG-01 remains the source of truth
- No duplicated graph logic
- Ask can answer market-wide relationship questions
- Research Workspace visualizes relationship networks
- Every relationship links to supporting evidence
