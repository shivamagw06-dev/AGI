# Track 3 — Institutional Research Office Runtime Dependency Map

**Knowledge-only consumer.** Soft-wire after Institutional Scheduler READY. No reasoning / KF / Ask / governance changes.

## Trigger

| Input | Condition | Output |
| --- | --- | --- |
| Scheduler morning run | `system_ready=True` (READY) | `research_office.run_morning_desk` |
| Manual / API | always allowed | same pipeline |

## Pipeline

```text
READY → Morning Publications (×8) → Company notes (evidence-triggered)
      → Research Queue → Watchlists → Publication Registry → Mission Control soft-read
      → READY FOR USERS
```

## Consumes (read-only)

| Source | Used for |
| --- | --- |
| IKS / layer dashboards | Macro, gov, industry, alt, expectations, events |
| KF coverage / evidence_feed | Coverage, company packs |
| Scheduler status / reports | Trigger context, agenda |
| Universe / sector soft boards | Sector report |

## Never produces

BUY · SELL · TARGET PRICE · PORTFOLIO ACTION

## Publication Registry fields

`id, title, created, knowledge_version, evidence_version, evidence_pack_versions, covered_entities, coverage, sources, generated_by, validation, status, historical_replay, point_in_time`
