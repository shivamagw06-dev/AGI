# L-01 — Launch Phase

**Mission:** Validate that AGIB solves real analyst workflows before expanding the product.

This is the first milestone driven by **usage**, not architecture.

**Prerequisite:** AGIB v1.0 GA (`docs/AGIB_V1_0_GA.md`)

---

## Principles

* Architecture remains frozen.
* No new intelligence engines.
* v1.1 capabilities stay behind feature flags until Launch-01 is healthy.
* Every roadmap item after Launch must be justified by observed user needs or measurable outcomes.

---

## Package

`intelligence-engine/institutional_launch/`

```text
analytics/          journey + events
feature_flags/      v1.1 flags (default off)
feedback/           👍 / 👎 + tags
product_metrics/    adoption dashboard
sla/                operational targets
launch_report.py    ready_for_v11 evidence
```

---

## Instrumented journey

```text
Login → Dashboard → Ask AGI → Research Workspace → Company → Portfolio → Publication → Export
```

Per stage: time spent, completion rate, errors, drop-offs.

Soft hooks on login, Ask, Workspace, and Publication — observe only.

---

## Product analytics

| Area | Metrics |
|------|---------|
| Adoption | DAU / WAU / MAU |
| Ask AGI | Questions, median/P95 latency, success, sources |
| Workspace | Sessions, notes, research opened, companies viewed |
| Publications | Generated, exported, shared |
| Portfolio Office | Decisions reviewed, committee sessions, risk updates |

---

## Feedback

Every surface can submit:

* `helpful` / `not_helpful`
* Optional tags: missing_data · wrong_answer · too_slow · hard_to_understand
* Optional comment → structured backlog candidates

---

## Operational SLAs

| Metric | Target |
|--------|-------:|
| Ask AGI P95 latency | &lt; 3 s |
| Data freshness | &lt; 30 min |
| Availability | 99.9% |
| Architecture conformance | 100% |
| Publication success | &gt; 99% |

---

## Feature flags (v1.1 gated)

```text
AI_REPORTS=false
COLLABORATION=false
GLOBAL_MARKETS=false
MACRO_LAB=false
AUTOMATION=false
EXTERNAL_INTEGRATIONS=false
AI_PRODUCTIVITY=false
```

---

## Mission Control — Launch Center

Soft-slice: `institutional_launch`

* Adoption · Ask P95 · Publications
* SLA status · Feedback · Feature flag rollout
* `ready_for_v11` recommendation

---

## APIs

* `GET /v1/launch/health|metrics|funnel|feedback|flags|sla|report`
* `POST /v1/launch/events|journey|feedback|flags`

---

## Success criteria → v1.1

Move to v1.1 only with evidence:

* Stable availability / SLAs green
* Conformance remains 100%
* Core workflows complete reliably
* Positive feedback trends
* Clear prioritized enhancement requests

### Sensible v1.1 sequence (after Launch-01)

1. Collaboration
2. Automation
3. Global Markets
4. External Integrations
5. AI Productivity (not recommendations)
