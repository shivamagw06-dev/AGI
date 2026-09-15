# PUB-01 — Publishing & Distribution

Phase 5.4 — Package institutional intelligence into deliverables.

## Architectural rule

> **PUB-01 never analyzes. It composes.**

No new recommendations, no new reasoning, no reinterpretation of evidence. It assembles immutable institutional objects into documents, dashboards, and recurring publications.

## Mission

Convert institutional intelligence into publication-ready outputs while preserving complete evidence lineage and reproducibility.

## Architecture

```text
                Universal Ask AGI
                       │
                       ▼
              Research Workspace
                       │
                       ▼
         Publishing & Distribution
                       │
             Publication Planner
                       │
                       ▼
             Publication Registry
                       │
             Publication Builder
                       │
          HTML / PDF / Markdown / JSON
                       │
                  Distribution
```

## Package

`intelligence-engine/institutional_publishing/`

## Core objects

```python
InstitutionalPublication(...)
PublicationManifest(...)  # authoritative audit record
```

Rendered HTML/PDF/Markdown/JSON are **presentation artifacts**. The **manifest** remains the authoritative audit record:

```json
{
  "publication_type": "MorningBrief",
  "template_version": "1.0.0",
  "generated_at": "...",
  "source_objects": ["InstitutionalDecision:123", "..."],
  "renderer": "pdf",
  "lineage_hash": "..."
}
```

## Publication registry

```python
register_publication(
    publication_type="MorningBrief",
    builder="MorningBrief_builder",
)
```

## API

- `POST /v1/publications/generate`
- `GET /v1/publications/{id}`
- `GET /v1/publications/types`
- `POST /v1/publications/export`

## Surfaces

- Research Workspace **Publications** tab
- Mission Control **Publication Center**
- Intelligence Map `PUB01`

## Invariants

- `analyzes: false`
- `generates_recommendations: false`
- `reinterprets_evidence: false`
- `compose_only: true`
- Templates control formatting, not analytical content
- Distribution is decoupled from builders

## Quality gates

Reject if: source objects missing, unresolved evidence, broken lineage, template invalid, duplicate ID, unsupported renderer.

## Success criteria

- Publications assembled exclusively from institutional objects
- Every output reproducible from immutable source objects + manifest
- Evidence lineage preserved end-to-end
- Multiple renderers share the same publication object
