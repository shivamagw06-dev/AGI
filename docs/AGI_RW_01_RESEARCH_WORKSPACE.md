# RW-01 — Institutional Research Workspace

Phase 5.2 — Analyst workstation over linked institutional objects.

## Mission

Transform AGI from a question-answering system into a **persistent research environment** where every object—company decisions, evidence, observations, portfolio actions, and committee outcomes—is connected.

The workspace answers:

> **"What is the complete investment story for this company or portfolio right now?"**

## Division of responsibilities

| Surface | Answers |
|---------|---------|
| **Ask AGI (UAG-01)** | *Where should I look?* |
| **Research Workspace (RW-01)** | *Show me everything that matters.* |

Ask is the entry point. The workspace is the primary day-to-day product.

## Architecture

```text
                Universal Ask AGI
                       │
                       ▼
              Research Workspace
                       │
 ┌─────────────┬─────────────┬──────────────┐
 ▼             ▼             ▼
Company     Portfolio     Research
Workspace   Workspace     Workspace
                       │
                       ▼
                 Object Viewer
                       │
                       ▼
 Evidence • Decisions • Risk • Policy
 Forecast • Observation • Committee
```

## Package

`intelligence-engine/institutional_workspace/`

- `workspace.py` — assemble company / portfolio / committee contexts
- `timeline.py` — chronological investment evolution
- `linked_objects.py` — clickable lineage navigation
- `evidence_browser.py` — filings and dependent objects
- `notes.py` — analyst-owned notes (never mutate system intelligence)
- `object_viewer.py` — normalize any institutional object for display
- `navigation.py` — nav items, in-workspace search, Ask ↔ Workspace deep links
- `diagnostics.py` — Workspace Health signals

## Core object

```python
InstitutionalWorkspace(
    workspace_id,
    context,
    active_object,
    timeline,
    linked_objects,
    diagnostics,
)
```

## Workspace contexts

Company · Portfolio · Committee · Research · Market · Macro — same framework.

## Invariants

- **Presentation / navigation only** — no new recommendations
- Analyst notes are separate from system-generated intelligence (`mutates_system_intelligence: false`)
- Full lineage navigable: Evidence → Decision → Risk → Policy → Portfolio Decision → Committee
- Timeline reconstructs investment evolution
- Domain engines remain systems of record

## API

- `GET /v1/workspace/health`
- `GET /v1/workspace/company/{ticker}`
- `GET /v1/workspace/portfolio/{id}`
- `GET /v1/workspace/object/{id}`
- `GET /v1/workspace/timeline/{id}`
- `GET /v1/workspace/search`
- `POST /v1/workspace/notes`

BFF: `/api/intelligence/workspace/...`

## UI

- `/agi/research` — Research Workspace (primary)
- Soft panels on company and portfolio pages
- Ask AGI responses deep-link into focused workspace sections
- Mission Control **Workspace Health** — missing links, evidence gaps, broken lineage, orphaned notes

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_workspace --company AXISBANK
PYTHONPATH=. python3 -m institutional_workspace --portfolio agi-core-equity
```

## Success criteria

- Every institutional object is navigable
- Complete lineage from evidence to committee is preserved
- Analysts can reconstruct investment history through the timeline
- Universal Ask AGI opens directly into the relevant workspace context
- Research notes coexist with—but never modify—system-generated intelligence
