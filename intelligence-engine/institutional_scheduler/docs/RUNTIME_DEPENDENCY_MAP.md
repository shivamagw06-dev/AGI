# Track 2 — Institutional Scheduler Runtime Dependency Map

**Contract for orchestration only.** Soft-wire to existing KF / IKS / Mission Control / Daily Health. No intelligence or reasoning changes.

## Morning DAG (06:00)

| Workflow ID | Depends on | Soft-wires to | Failure policy |
| --- | --- | --- | --- |
| `universe_update` | — | `universe_intelligence` pipeline | isolate + continue |
| `historical_update` | universe | KF `run_daily_pipeline(historical_depth=True)` soft / HD pipeline | isolate |
| `company_intelligence` | historical | ICI pipeline | isolate |
| `corporate_events` | company | ICEI pipeline | isolate |
| `government_intelligence` | historical | IGRI pipeline (parallel-ok with company) | isolate |
| `industry_intelligence` | company | IIVI pipeline | isolate |
| `economic_relationships` | industry | IERI pipeline | isolate |
| `alternative_data` | relationships | IADI pipeline | isolate; mark unavailable |
| `market_expectations` | alternative_data (soft) + company | IMEI pipeline | isolate |
| `evidence_pack_generation` | company + expectations | KF evidence packs / Track-1 daily soft | regenerate without failed layers |
| `coverage_validation` | evidence | KF coverage / morning coverage | gate input |
| `quality_gates` | coverage | scheduler gate evaluator | READY=false on fail |
| `mission_control` | quality_gates | `mission_control.aggregate` soft-read | isolate |
| `daily_health` | quality_gates | `daily_health_scorecard` | isolate |
| `research_queue` | daily_health + mission_control | queue builder (knowledge-only) | isolate |
| `morning_reports` | research_queue | report generators (no recommendations) | isolate |
| `ready_declaration` | morning_reports + quality_gates | sets operational state | — |

## Parallel levels

1. `universe_update`
2. `historical_update`
3. `company_intelligence` ‖ `government_intelligence`
4. `corporate_events`
5. `industry_intelligence`
6. `economic_relationships`
7. `alternative_data`
8. `market_expectations`
9. `evidence_pack_generation`
10. `coverage_validation`
11. `quality_gates`
12. `mission_control` ‖ `daily_health`
13. `research_queue`
14. `morning_reports`
15. `ready_declaration`

## Operational states

`INITIALISING` → `RUNNING` → `PARTIAL_READY` | `READY` | `WARNING` | `FAILED` | `MAINTENANCE`
