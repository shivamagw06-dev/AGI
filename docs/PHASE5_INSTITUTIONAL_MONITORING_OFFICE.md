# AGI v4.0 Phase 5 Sprint 5.4 — Institutional Monitoring Office (IMO)

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
MODULE: IMO
VERSION: institutional-monitoring-office-v1.0.0
SCHEMA: imo-event-schema-v1.0.0
```

## Philosophy

Monitoring is more than alerts. A CIO asks **What changed?** — not merely **What happened?**

```text
Portfolio Idea → Continuous Monitoring → MonitoringEvent → Review recommendation
```

Events **recommend review**. They never mutate thesis, decision, or portfolio idea.

## Layering

| Object | Question |
|--------|----------|
| Investment Thesis | Why is this interesting? |
| Investment Decision | What governance action? |
| Portfolio Idea | How does this compare? |
| **MonitoringEvent** | What changed that requires attention? |
| Position (later) | Has capital been allocated? |

## MonitoringEvent fields

event_id · portfolio_idea · trigger · source · severity ·
affected_thesis · affected_decision · affected_confidence ·
recommended_action · requires_review · timestamp

## Domains

Earnings · Guidance · Management Commentary · Corporate Actions ·
Regulatory · Macro · Sector · Competitor · Valuation · Confidence

## Recommended actions

Review · Committee Review · Escalate · Refresh Thesis · Monitor · No Action

## Example triggers

| Trigger | Action |
|---------|--------|
| Confidence dropped >10 | Review |
| Bull case invalidated | Committee Review |
| Guidance withdrawn | Escalate |
| Quarterly results published | Refresh Thesis |

## APIs

`/v1/monitoring/{health,dashboard,telemetry,history,create,list,review-queue,:event_id}`

## Measurement

**MQS** — Monitoring Quality Score (independent of CIO / PQS / prior metrics).

Components: trigger relevance · false-positive discipline · event traceability ·
review recommendation quality · latency · monitoring coverage · explainability

## LangSmith

`monitoring_office` after `portfolio_office`, before `reasoning.governance`.

## Hard rules

* Consume ITE / IDO / IPO — do not redesign them  
* Events do not modify living objects  
* No positions / orders / execution  
* Soft-wire only into Ask pipeline + IEL probe  
