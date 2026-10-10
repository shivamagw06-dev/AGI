# WO-01 — Watchlist Office

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — Portfolio Domain (research queue) |
| **Workstream** | WO-01 |
| **Package** | `intelligence-engine/watchlist_office/` |
| **Consumes** | Office SDK · PEB-01 · IO-01 / FIRE references (read-only) |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Office SDK · PEB · IO/CIO/PO |

> Watchlist Office answers: *Which companies are in my research queue, and what existing intelligence last touched them?*

---

# 1. Mission

Watchlists are **research queues**, not ticker lists.

- Never performs research or recalculates FIRE  
- Never emits BUY / SELL  
- Publishes `watchlist.company.added` / `watchlist.company.removed`  
- Subscribes to research / quality / execution / comparison events via PEB-01  

---

# 2. Entry metadata

Company · Tags · Priority · Status (New / Reviewing / Monitoring / Archived) · Notes · Last research / comparison / quality / execution timestamps · Last event received

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--watchlist Core` | `GET /v1/watchlist-office/{id}` |
| `--add Core TCS` | `POST /v1/watchlist-office` · `POST .../companies` |
| `--queue Core` | `GET .../queue` |

Office SDK: `office_id=wo-01`
