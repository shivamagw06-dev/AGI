# AGI — Institutional Coverage Factory (ICF-01)

## Mission

Build a factory that continuously drives companies toward **Institutional Coverage Complete (ICC)**.

Every company progresses through the same pipeline automatically, 24×7.

```text
Universe
        ↓
Coverage Planner
        ↓
Acquire Missing Evidence
        ↓
Normalize
        ↓
Validate
        ↓
Evidence Registry
        ↓
Company Memory
        ↓
Knowledge Graph
        ↓
Research Readiness
        ↓
Institutional Coverage Complete
```

## North star metric

**Companies entering ICC per day** — not companies crawled per day.

`max_companies_per_day` is a configurable ICC throughput target. Scale to 250 or 500 without redesign.

## Package

`intelligence-engine/institutional_coverage_factory/`

| Module | Role |
|--------|------|
| `planner/` | Rank non-ICC companies; queue missing collectors |
| `collectors/` | Soft bridges per evidence class (CGL / KF / FSE / IEP / KIL) |
| `validator/` | ICC exit criteria |
| `scorer/` | Weighted evidence-class coverage % |
| `scheduler/` | Rolling 15-minute ticks |
| `dashboards/` | Mission Control Coverage board |
| `api/` / `production.py` | Engine façades |

## Coverage model

Required evidence classes (weights sum = 100):

| Category | Required | Weight |
|----------|----------|-------:|
| Annual Reports | Yes | 10 |
| Quarterly Results | Yes | 10 |
| Financial Statements | Yes | 20 |
| Earnings Presentations | Yes | 10 |
| Earnings Call Transcripts | Yes | 10 |
| Shareholding | Yes | 10 |
| Corporate Actions | Yes | 5 |
| Management Guidance | Yes | 5 |
| Segment KPIs | Yes | 10 |
| Company Memory | Yes | 5 |
| Knowledge Graph | Yes | 5 |

## Priority

1. TOP20 (IEP Phase-1 cross-sector set)
2. NIFTY50
3. NIFTY100
4. UNIVERSE (Nifty 500)

## Scheduling

Every 15 minutes (configurable):

```text
Coverage Planner → select next companies → dispatch collectors
→ KIL integrate → validate → update score / ICC → repeat
```

Already-complete companies are skipped for acquisition; only refresh what changed.

## Config

```yaml
coverage_factory:
  enabled: true
  max_companies_per_day: 100          # ICC entries / day
  max_parallel_collectors: 20
  priority:
    - TOP20
    - NIFTY50
    - NIFTY100
    - UNIVERSE
  retry_policy:
    max_attempts: 5
  coverage_threshold: 90
  institutional_coverage_threshold: 100
```

Env overrides: `AGI_ICF_ENABLED`, `AGI_ICF_MAX_COMPANIES_PER_DAY`, `AGI_ICF_MAX_PARALLEL_COLLECTORS`, `AGI_ICF_TICK_INTERVAL_MINUTES`, `AGI_ICF_COMPANIES_PER_TICK`, `AGI_ICF_COVERAGE_THRESHOLD`, `AGI_ICF_ICC_THRESHOLD`, `AGI_ICF_DISPATCH_ENABLED`, `AGI_ICF_SCHEDULER_ENABLED`.

## ICC exit criteria

A company becomes ICC only if:

* All mandatory evidence types are present
* Canonical financial statements are published
* Evidence Registry is complete
* Company Memory is populated
* Knowledge Graph is refreshed
* Research Readiness ≥ threshold
* Knowledge Confidence ≥ threshold
* `claim_safe == true`
* A research note can be generated with material claims traceable to primary evidence

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/icf/health` | Health |
| GET | `/v1/icf/status` | Identity + config |
| GET | `/v1/icf/dashboard` | Coverage board |
| GET | `/v1/icf/score/{ticker}` | Weighted coverage |
| GET | `/v1/icf/icc/{ticker}` | ICC exit evaluation |
| GET | `/v1/icf/plan` | Planner queue (no side effects) |
| POST | `/v1/icf/plan-dispatch` | Plan + dispatch collectors |
| POST | `/v1/icf/tick` | One rolling scheduler tick |
| POST | `/v1/icf/dispatch/{ticker}` | Dispatch gaps for one company |
| GET | `/v1/icf/scheduler` | Daily ICC capacity / tick state |

BFF: `/api/intelligence/icf/*`

## Mission Control

**Institutional Coverage · ICF-01** soft slice: ICC today, daily target, capacity left, tick interval, priority.

Live board: `GET /api/intelligence/icf/dashboard?scope=TOP20`

## Soft-wire

Collectors call existing engines only (no second acquisition stack):

* FSE ingest/publish for financials / segments
* IEP acquisition for registry documents
* KIL `integrate_company` + auto-repair after gaps
* CGL / earnings / LIDI for transcripts, presentations, shareholding, corp actions

## Milestone focus (product)

1. Top 20 reach operational coverage (>90%) first
2. Raise configurable ICC throughput once collectors are reliable
3. Expand remaining universe while holding research quality gates
