# PEB-01 — Platform Event Bus

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — Platform Layer (infrastructure) |
| **Workstream** | PEB-01 |
| **Package** | `intelligence-engine/platform_event_bus/` |
| **Role** | In-process typed pub/sub coordination |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Office SDK · IO/CIO/PO |

> The Event Bus answers: *How do AGIB components communicate without becoming tightly coupled?*

---

# 1. Mission

Lightweight internal event bus. Publish / subscribe typed events.

- Never performs business logic  
- Never modifies intelligence or FIRE outputs  
- Synchronous, in-process, at-most-once  
- No Kafka / Redis / persistence / retries  

Architecture allows a future broker-backed replacement behind the same publisher API.

---

# 2. Surfaces

| CLI | REST |
| --- | --- |
| `--statistics` | `GET /v1/platform/events/statistics` |
| `--events` | `GET /v1/platform/events` |
| `--types` | `GET /v1/platform/events/types` |

Optional soft publication from IO-01 / CIO-01 / PO-01 (offices unchanged if bus unavailable).
