# FSE-00 — Pipeline Orchestrator (Phase 0)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — additive coordination layer |
| **Workstream** | FSE-00 / Phase 0 |
| **Package** | `intelligence-engine/financial_statements_engine/orchestrator/` |
| **Reuses** | FSE Event Bus (`collection/event_bus.py`) · FSE store · engine production façades |
| **Does not** | Parse · validate · warehouse · calculate · migrate HD · change collectors |

> **Intent:** Coordinate existing FSE engines as a deterministic workflow. Business logic stays inside each engine. The orchestrator only schedules, tracks state, retries, replays, and observes.

---

## Workflow

```text
RAW_EVIDENCE_STORED → PARSE → VALIDATE → WAREHOUSE_PUBLISH → DERIVED_METRICS
```

## Workflow identity

`company_id` + `period` + `filing_type` + `document_hash` → unique `workflow_id`  
Duplicates do not execute twice.

## State machine

`RECEIVED` · `QUEUED` · `RUNNING` · `COMPLETED` · `FAILED` · `RETRYING` · `CANCELLED`

## Production auto-start (required)

```text
evidence.stored  →  Orchestrator  →  PARSE → VALIDATE → WAREHOUSE → DME
```

`bind_orchestrator_subscriber()` is wired in **app lifespan** (`app/main.py`). No manual trigger required for the happy path.

## Dead Letter Queue

```text
FAILED → Retry (max 3, exponential backoff) → DEAD_LETTER
```

Permanent failures also enter `DEAD_LETTER`. Mission Control `/orchestrator/dlq` shows:

| Field | Meaning |
| --- | --- |
| workflow_id | Unique workflow |
| company / ticker | Entity |
| stage | Failing stage |
| error | Reason |
| last_retry | Last retry timestamp |
| manual_replay_action | `POST …/orchestrator/replay/{id}` |

## Surfaces

| Surface | Path |
| --- | --- |
| Health / Dashboard | `--orch-health` · `--orch-dashboard` · `GET …/orchestrator/health|dashboard` |
| Queue / History / DLQ | `--orch-queue` · `--orch-history` · `--orch-dlq` · `GET …/orchestrator/{workflows,dlq}` |
| Retry / Replay | `--orch-retry ID` · `--orch-replay ID` · `POST …/orchestrator/retry|replay/{id}` |

## Foundation choice

Built **on top of** the existing FSE Event Bus + disk store (JSONL events, JSON workflow records). No second Celery/RQ scheduler introduced. CGL remains the gather loop; this orchestrator owns FSE stage sequencing only.
