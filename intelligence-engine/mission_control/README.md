# AGI Mission Control V1

**Architecture status:** v1.0.1 LOCKED  
**Role:** Administrator-only operations cockpit.  
**Delivery:** Worker-built snapshot · HTTP read-only  
**Not:** intelligence engine · recommendation engine · client page · mutator

## Rules

- Read-only aggregation of IOC, CMS, CID, Academy, CA, IO, DVC, ECP, …
- Never modifies research, House Views, or recommendations
- Never visible to public/clients
- **HTTP never runs `build_mission_control()`** — see `docs/AGI_MC_SNAPSHOT.md`

## Admin

`/admin/mission-control` — polls snapshot every 90s, health every 45s

## Flags

`MISSION_CONTROL`, `MISSION_CONTROL_APIS`, `MISSION_CONTROL_PLATFORMS`, `MISSION_CONTROL_COVERAGE`, `MISSION_CONTROL_KNOWLEDGE`, `MISSION_CONTROL_ALERTS`, `MISSION_CONTROL_EVENTS`, `MISSION_CONTROL_REPORTS`

## APIs

- `GET /v1/mission-control/health` — liveness + snapshot meta
- `GET /v1/mission-control/dashboard` — snapshot reader (or warming)
- `GET /v1/mission-control/agent-map` — Agent Map snapshot reader (or warming)
- `GET /v1/mission-control/intelligence-map` — Intelligence Map snapshot reader (or warming)
- `GET /v1/mission-control/institutional-intelligence` — Institutional Intelligence snapshot reader (or warming)
- `POST /v1/mission-control/rebuild` — queue background rebuild (+ Agent Map)
- `GET /v1/mission-control/quality-gates`
- `GET /v1/mission-control/report`
- `POST /v1/mission-control/acknowledge`
