# AGI V1.2 — Knowledge Operations Center (KOC)

## Institutional Knowledge Mission Control

Admin-only command center for the Institutional Knowledge Operating System.

**Not a developer dashboard.** Operators monitor, validate, repair, and improve institutional knowledge before research is published.

## Access

| Rule | Behavior |
|------|----------|
| Admin (`isAdmin`) | **Knowledge Operations** in top nav + CMS sidebar |
| Non-admin | Menu hidden; direct URL → **403 Forbidden** |
| Every action | Immutable audit log |

Route: `/admin/knowledge-operations` (alias `/knowledge-operations`)

## Design

White modern institutional UI · Bloomberg precision · Green / Orange / Red / Blue status only.

## Primary workflow

**Missing Knowledge Inbox** + **Knowledge Gap AI** — clear prioritized gaps with estimated ICC / confidence / readiness uplift. One-click Upload.

## Sections

1. Today's Knowledge Timeline  
2. Institutional Coverage Dashboard  
3. Company Detail (checklist)  
4. Missing Knowledge Inbox  
5. Manual Knowledge Upload (append-only pipeline)  
6. Knowledge Queue  
7. Collector Health  
8. Evidence Explorer  
9. Knowledge Graph Viewer  
10. Knowledge Version History  
11. Coverage Heatmap  
12. Knowledge Gap AI  
13. Operations  
14. Audit Trail  

## System Health Bar

CGL · KIL · ICF · Scheduler · Collector Health % · Knowledge Latency · Repair Queue · Auto Repair · KOC

## Package

`intelligence-engine/knowledge_operations/`

| Module | Role |
|--------|------|
| `desk.py` / `production.py` | Overview aggregate |
| `system_health.py` | Health bar |
| `missing_inbox.py` | Prioritized gaps + ICC gain |
| `gap_ai.py` | Coverage / confidence / readiness uplift |
| `evidence_explorer.py` | Search + lineage |
| `upload.py` | Manual upload pipeline |
| `audit.py` | Immutable audit |
| `actions.py` | Audited ops |

## APIs

| Method | Path |
|--------|------|
| GET | `/v1/koc/overview` · `/system-health` · `/coverage` |
| GET | `/v1/koc/company/{ticker}` · `/missing-knowledge` |
| GET | `/v1/koc/collectors` · `/evidence` · `/knowledge-versions` |
| GET | `/v1/koc/gap-ai` · `/search` · `/audit` · `/queue` |
| POST | `/v1/koc/upload` · `/run-cgl` · `/run-kil` · `/run-coverage` · `/repair` |

BFF: `/api/intelligence/koc/*`

## Success criteria

- Complete visibility into CGL → KIL → IEP → ICF → Memory → Graph → Research  
- Measurable Institutional Coverage per company  
- Missing documents automatically identified  
- Manual upload updates memory, graph, readiness  
- Research traceable to immutable evidence  
- Overnight Knowledge Snapshots observable  
- Every admin action audited  
