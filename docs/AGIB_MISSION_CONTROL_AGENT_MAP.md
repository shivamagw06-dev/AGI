# Mission Control · Agent Map

Administrator button on `/admin/mission-control` that lists every AGIB agent and whether it is **working**, **soft-wire**, **off**, or **orphan**.

## API

- Engine: `GET /v1/mission-control/agent-map`
- Node proxy: `GET /api/intelligence/mission-control/agent-map`  
  (enriches Node-only flags: `CIO_MORNING_SCHEDULER`, `CMS_INGEST_WORKER_MODE`)

## Status legend

| Status | Meaning |
| --- | --- |
| **working** | Intended to run in production and currently available |
| **soft** | Available as soft-wire / seeded / ops-only — not a continuous primary loop |
| **off** | Disabled by production flag |
| **orphan** | Source missing or not importable |
| **degraded** | Module present but health probe failed |

## UI

- Header button: **Agent Map**
- Section card: **Open Agent Map**
- Panel shows filter chips, per-group agent buttons, responsibility, data sources, and status detail

## Code

- `intelligence-engine/mission_control/agent_map.py`
- `src/pages/admin/AgentMapPanel.jsx`
- `src/pages/admin/MissionControl.jsx`
