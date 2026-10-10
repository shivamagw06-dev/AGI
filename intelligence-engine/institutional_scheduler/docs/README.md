# Institutional Scheduler (AGIB v2.1 Track 2)

Operational heartbeat for morning knowledge refresh. **No intelligence. No reasoning.**

## Contract

See `RUNTIME_DEPENDENCY_MAP.md`.

## Run

```python
from institutional_scheduler import run_morning
run_morning(dry_run=False, parallel=True)
```

## APIs

- `GET /v1/scheduler/status|health|history|workflows|reports|telemetry|dashboard`
- `POST /v1/scheduler/run` body: `{dry_run, parallel, skip, manual_override, operator_notes}`
- `POST /v1/scheduler/retry` body: `{workflow_id, run_id?, dry_run?}`

## States

`INITIALISING | RUNNING | PARTIAL_READY | READY | WARNING | FAILED | MAINTENANCE`
