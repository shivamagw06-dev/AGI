# Institutional Research Office (IROffice)

AGIB’s research desk. Consumes Knowledge Factory / IKS / Scheduler outputs and publishes evidence-backed morning research.

**Never** emits BUY / SELL / TARGET PRICE / PORTFOLIO ACTION.

## Trigger

`InstitutionalScheduler` → READY → `research_office.run_after_scheduler_ready`

## Publication Registry

Every publication is versioned with knowledge/evidence versions, covered entities, validation, and point-in-time replay ids.
