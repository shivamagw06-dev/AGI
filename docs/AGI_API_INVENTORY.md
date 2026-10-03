# AGI Intelligence Engine — API Inventory & Health

**Probed:** 2026-07-28 · in-process ASGI probe of every parameterless `GET`

## Summary

- Total routes: **991** across **124** domains (all under `/v1`)
- Parameterless `GET` probed: **609**
- **534 returned 200**
- 61 returned 422 (endpoint works; a required query param such as `q` was omitted)
- 7 returned 401 (endpoint works; needs `Authorization: Bearer <INTELLIGENCE_ENGINE_TOKEN>`)
- 6 returned 404 (endpoint works; no warm state/run yet — `cre`, `e01`, `e03`, `e10`, `e14`)
- 1 slow: `/v1/company-dossier/quality-gates` (~49 s, returns 200)
- 0 endpoints returned 5xx

## Domain health

| Domain | Routes | GET 200 | Needs param (422) | Needs auth (401) | No data (404) |
|--------|------:|-------:|------------------:|-----------------:|--------------:|
| `academy` | 69 | 43 | 1 | 0 | 0 |
| `accounting-intelligence` | 6 | 3 | 0 | 0 | 0 |
| `acquisition-planner` | 7 | 4 | 0 | 0 | 0 |
| `admin` | 14 | 14 | 0 | 0 | 0 |
| `ail` | 4 | 2 | 1 | 0 | 0 |
| `aip` | 14 | 9 | 0 | 0 | 0 |
| `alternative-data` | 11 | 5 | 1 | 0 | 0 |
| `analyst-router` | 6 | 4 | 0 | 0 | 0 |
| `answer-construction` | 1 | 1 | 0 | 0 | 0 |
| `aoi` | 12 | 7 | 2 | 0 | 0 |
| `ask` | 6 | 3 | 3 | 0 | 0 |
| `aws` | 13 | 7 | 1 | 0 | 0 |
| `belief-engine` | 6 | 4 | 0 | 0 | 0 |
| `cae` | 11 | 4 | 4 | 0 | 0 |
| `causal-intelligence` | 7 | 4 | 0 | 0 | 0 |
| `company` | 7 | 0 | 0 | 0 | 0 |
| `company-analysis` | 6 | 4 | 0 | 0 | 0 |
| `company-dossier` | 10 | 2 | 0 | 0 | 0 |
| `company-intelligence` | 7 | 5 | 0 | 0 | 0 |
| `company-monitor` | 8 | 6 | 0 | 0 | 0 |
| `company-timeline` | 1 | 0 | 0 | 0 | 0 |
| `context-intelligence` | 6 | 4 | 0 | 0 | 0 |
| `contradiction-reasoning` | 1 | 1 | 0 | 0 | 0 |
| `corporate-events` | 5 | 3 | 0 | 0 | 0 |
| `cre` | 7 | 3 | 0 | 0 | 2 |
| `debate-engine` | 6 | 4 | 0 | 0 | 0 |
| `decision-engine-v2` | 8 | 4 | 0 | 0 | 0 |
| `decision-quality` | 14 | 11 | 0 | 0 | 0 |
| `decision-readiness` | 6 | 4 | 0 | 0 | 0 |
| `documents` | 7 | 4 | 0 | 0 | 0 |
| `dvc` | 8 | 5 | 0 | 0 | 0 |
| `e01` | 3 | 2 | 0 | 0 | 1 |
| `e02` | 3 | 1 | 0 | 0 | 0 |
| `e03` | 4 | 1 | 0 | 0 | 1 |
| `e04` | 3 | 1 | 0 | 0 | 0 |
| `e05` | 3 | 1 | 0 | 0 | 0 |
| `e08` | 3 | 1 | 0 | 0 | 0 |
| `e09` | 3 | 1 | 0 | 0 | 0 |
| `e10` | 3 | 2 | 0 | 0 | 1 |
| `e11` | 4 | 1 | 0 | 0 | 0 |
| `e13` | 3 | 1 | 0 | 0 | 0 |
| `e14` | 3 | 2 | 0 | 0 | 1 |
| `ecp` | 6 | 4 | 0 | 0 | 0 |
| `editorial` | 1 | 1 | 0 | 0 | 0 |
| `entity-resolution` | 6 | 4 | 0 | 0 | 0 |
| `eval` | 2 | 0 | 0 | 1 | 0 |
| `eve` | 14 | 9 | 2 | 0 | 0 |
| `event` | 1 | 0 | 0 | 0 | 0 |
| `events` | 2 | 2 | 0 | 0 | 0 |
| `evidence` | 8 | 3 | 2 | 0 | 0 |
| `expectations` | 12 | 8 | 1 | 0 | 0 |
| `faa` | 8 | 4 | 2 | 0 | 0 |
| `features` | 8 | 1 | 0 | 4 | 0 |
| `filing-diff` | 7 | 3 | 0 | 0 | 0 |
| `filing-intelligence` | 9 | 3 | 0 | 0 | 0 |
| `fiml` | 15 | 6 | 1 | 0 | 0 |
| `fle` | 20 | 8 | 2 | 0 | 0 |
| `forecast` | 7 | 3 | 0 | 0 | 0 |
| `framework-selection` | 6 | 4 | 1 | 0 | 0 |
| `fre` | 14 | 7 | 3 | 0 | 0 |
| `government` | 13 | 11 | 0 | 0 | 0 |
| `health` | 1 | 1 | 0 | 0 | 0 |
| `hypothesis-engine` | 6 | 4 | 0 | 0 | 0 |
| `hypothesis-testing` | 6 | 4 | 0 | 0 | 0 |
| `ib` | 14 | 9 | 0 | 0 | 0 |
| `iie` | 21 | 8 | 4 | 0 | 0 |
| `ilm` | 9 | 3 | 0 | 0 | 0 |
| `industry` | 12 | 3 | 6 | 0 | 0 |
| `institutional-analog-intelligence` | 6 | 4 | 1 | 0 | 0 |
| `institutional-analysts` | 2 | 2 | 0 | 0 | 0 |
| `institutional-communication` | 3 | 3 | 0 | 0 | 0 |
| `institutional-evaluation-lab` | 7 | 6 | 0 | 0 | 0 |
| `institutional-evidence-graph` | 5 | 3 | 1 | 0 | 0 |
| `institutional-knowledge` | 4 | 2 | 0 | 0 | 0 |
| `institutional-playbooks` | 6 | 4 | 1 | 0 | 0 |
| `institutional-reasoning` | 9 | 6 | 1 | 0 | 0 |
| `institutional-stack` | 7 | 3 | 0 | 0 | 0 |
| `investment-committee` | 4 | 2 | 0 | 0 | 0 |
| `investment-office` | 4 | 3 | 0 | 0 | 0 |
| `ioc` | 6 | 6 | 0 | 0 | 0 |
| `irp` | 3 | 2 | 0 | 0 | 0 |
| `kc` | 9 | 6 | 1 | 0 | 0 |
| `kf` | 15 | 8 | 1 | 0 | 0 |
| `kip` | 25 | 2 | 3 | 0 | 0 |
| `knowledge-factory` | 44 | 22 | 0 | 0 | 0 |
| `knowledge-graph` | 8 | 3 | 1 | 0 | 0 |
| `l4` | 3 | 1 | 0 | 0 | 0 |
| `layer-router` | 6 | 4 | 0 | 0 | 0 |
| `leo` | 5 | 3 | 0 | 0 | 0 |
| `live-data` | 16 | 13 | 0 | 0 | 0 |
| `management-intelligence` | 7 | 3 | 0 | 0 | 0 |
| `market-data` | 1 | 1 | 0 | 0 | 0 |
| `mee` | 18 | 6 | 2 | 0 | 0 |
| `mission-control` | 5 | 4 | 0 | 0 | 0 |
| `orch` | 6 | 2 | 0 | 1 | 0 |
| `patch-intelligence` | 2 | 2 | 0 | 0 | 0 |
| `peer-intelligence` | 8 | 5 | 0 | 0 | 0 |
| `portfolio-intelligence` | 7 | 3 | 0 | 0 | 0 |
| `prediction` | 1 | 0 | 0 | 0 | 0 |
| `reasoning-audit` | 6 | 4 | 0 | 0 | 0 |
| `red-team` | 1 | 1 | 0 | 0 | 0 |
| `relationship` | 14 | 4 | 2 | 0 | 0 |
| `research` | 3 | 0 | 0 | 1 | 0 |
| `research-blueprint` | 7 | 4 | 0 | 0 | 0 |
| `research-execution` | 9 | 4 | 0 | 0 | 0 |
| `research-objective` | 6 | 4 | 0 | 0 | 0 |
| `research-office` | 8 | 6 | 1 | 0 | 0 |
| `research-ontology` | 5 | 4 | 0 | 0 | 0 |
| `research-questions` | 6 | 4 | 0 | 0 | 0 |
| `research-writer` | 2 | 2 | 0 | 0 | 0 |
| `rms` | 8 | 2 | 0 | 0 | 0 |
| `root-cause-intelligence` | 6 | 6 | 0 | 0 | 0 |
| `rsp` | 6 | 1 | 0 | 0 | 0 |
| `scheduler` | 9 | 7 | 0 | 0 | 0 |
| `sif` | 6 | 4 | 0 | 0 | 0 |
| `simulation` | 7 | 5 | 0 | 0 | 0 |
| `temporal-integrity` | 7 | 6 | 0 | 0 | 0 |
| `thesis-engine` | 6 | 4 | 0 | 0 | 0 |
| `ui` | 17 | 10 | 0 | 0 | 0 |
| `universe-intelligence` | 12 | 5 | 1 | 0 | 0 |
| `validation` | 6 | 3 | 0 | 0 | 0 |
| `validation-engine` | 8 | 4 | 0 | 0 | 0 |
| `ve` | 12 | 2 | 7 | 0 | 0 |
| `yfp` | 5 | 3 | 1 | 0 | 0 |

## Full route list

### `academy`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/academy/accounting` | WORKING (337 ms) |
| POST | `/v1/academy/books/attach-kf` | not probed |
| GET | `/v1/academy/books/dashboard` | WORKING (1071 ms) |
| GET | `/v1/academy/books/graph` | WORKING (12 ms) |
| GET | `/v1/academy/books/health` | WORKING (3 ms) |
| POST | `/v1/academy/books/ingest` | not probed |
| POST | `/v1/academy/books/ingest-library` | not probed |
| GET | `/v1/academy/books/ingestion-report` | WORKING (9 ms) |
| GET | `/v1/academy/books/library` | WORKING (11 ms) |
| POST | `/v1/academy/books/package` | not probed |
| GET | `/v1/academy/books/quality-gates` | WORKING (5 ms) |
| GET | `/v1/academy/books/v3/analyst/{analyst}` | not probed |
| POST | `/v1/academy/books/v3/ask` | not probed |
| GET | `/v1/academy/books/v3/dashboard` | WORKING (3 ms) |
| GET | `/v1/academy/books/v3/health` | WORKING (3 ms) |
| GET | `/v1/academy/books/v3/quality-gates` | WORKING (4 ms) |
| GET | `/v1/academy/causal-models` | WORKING (3 ms) |
| GET | `/v1/academy/certification/dashboard` | WORKING (117 ms) |
| POST | `/v1/academy/certification/exam/{exam_id}` | not probed |
| POST | `/v1/academy/certification/gate` | not probed |
| GET | `/v1/academy/certification/health` | WORKING (3 ms) |
| GET | `/v1/academy/certification/inventory` | WORKING (10 ms) |
| GET | `/v1/academy/certification/quality-gates` | WORKING (35 ms) |
| POST | `/v1/academy/certification/run` | not probed |
| GET | `/v1/academy/completion` | WORKING (1773 ms) |
| GET | `/v1/academy/concepts` | WORKING (6 ms) |
| GET | `/v1/academy/concepts/{concept_id}` | not probed |
| POST | `/v1/academy/consumer/{engine}` | not probed |
| GET | `/v1/academy/corporate-finance` | WORKING (4 ms) |
| GET | `/v1/academy/course` | WORKING (3 ms) |
| GET | `/v1/academy/courses` | WORKING (3 ms) |
| GET | `/v1/academy/dashboard` | WORKING (43 ms) |
| POST | `/v1/academy/earnings-quality` | not probed |
| GET | `/v1/academy/enrich/{concept_id}` | not probed |
| GET | `/v1/academy/evidence/case/{case_id}` | not probed |
| POST | `/v1/academy/evidence/confidence` | not probed |
| GET | `/v1/academy/evidence/dashboard` | WORKING (19 ms) |
| GET | `/v1/academy/evidence/health` | WORKING (3 ms) |
| GET | `/v1/academy/evidence/quality-gates` | WORKING (4 ms) |
| POST | `/v1/academy/evidence/support` | not probed |
| GET | `/v1/academy/exams` | WORKING (22 ms) |
| GET | `/v1/academy/exams/{question_id}` | not probed |
| GET | `/v1/academy/graph` | WORKING (10 ms) |
| GET | `/v1/academy/health` | WORKING (683 ms) |
| GET | `/v1/academy/mental-models` | WORKING (4 ms) |
| GET | `/v1/academy/metrics` | WORKING (3 ms) |
| GET | `/v1/academy/neighborhood/{concept_id}` | not probed |
| GET | `/v1/academy/production` | WORKING (1495 ms) |
| GET | `/v1/academy/production/ab` | WORKING (176 ms) |
| POST | `/v1/academy/production/package` | not probed |
| GET | `/v1/academy/production/quality-gates` | WORKING (1419 ms) |
| GET | `/v1/academy/provenance` | WORKING (403 ms) |
| GET | `/v1/academy/quality` | WORKING (11 ms) |
| GET | `/v1/academy/red-flags` | WORKING (3 ms) |
| POST | `/v1/academy/red-flags/score` | not probed |
| GET | `/v1/academy/regression/dashboard` | WORKING (3848 ms) |
| POST | `/v1/academy/regression/gate` | not probed |
| GET | `/v1/academy/regression/health` | WORKING (4 ms) |
| GET | `/v1/academy/regression/history` | WORKING (3 ms) |
| GET | `/v1/academy/regression/quality-gates` | WORKING (25 ms) |
| POST | `/v1/academy/regression/run` | not probed |
| GET | `/v1/academy/search` | WORKING — needs query param |
| GET | `/v1/academy/teach/{concept_id}` | not probed |
| GET | `/v1/academy/validation/dashboard` | WORKING (25 ms) |
| POST | `/v1/academy/validation/exam/{exam_id}` | not probed |
| GET | `/v1/academy/validation/exams` | WORKING (4 ms) |
| GET | `/v1/academy/validation/health` | WORKING (2 ms) |
| GET | `/v1/academy/validation/quality-gates` | WORKING (28 ms) |
| POST | `/v1/academy/validation/run` | not probed |

### `accounting-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/accounting-intelligence/analyse` | not probed |
| GET | `/v1/accounting-intelligence/company/{ticker}` | not probed |
| GET | `/v1/accounting-intelligence/dashboard` | WORKING (3 ms) |
| GET | `/v1/accounting-intelligence/health` | WORKING (3 ms) |
| GET | `/v1/accounting-intelligence/history/{ticker}` | not probed |
| GET | `/v1/accounting-intelligence/quality-gates` | WORKING (7 ms) |

### `acquisition-planner`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/acquisition-planner/constitution` | WORKING (5 ms) |
| GET | `/v1/acquisition-planner/dashboard` | WORKING (178 ms) |
| POST | `/v1/acquisition-planner/diagnostics` | not probed |
| POST | `/v1/acquisition-planner/enrich` | not probed |
| GET | `/v1/acquisition-planner/health` | WORKING (3 ms) |
| POST | `/v1/acquisition-planner/plan` | not probed |
| GET | `/v1/acquisition-planner/quality-gates` | WORKING (173 ms) |

### `admin`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/admin/accounting-intelligence` | WORKING (11 ms) |
| GET | `/v1/admin/causal-intelligence` | WORKING (290 ms) |
| GET | `/v1/admin/decision-engine-v2` | WORKING (1195 ms) |
| GET | `/v1/admin/filing-diff` | WORKING (10 ms) |
| GET | `/v1/admin/filing-intelligence` | WORKING (9 ms) |
| GET | `/v1/admin/forecast-intelligence` | WORKING (214 ms) |
| GET | `/v1/admin/institutional-memory` | WORKING (12 ms) |
| GET | `/v1/admin/institutional-stack` | WORKING (2164 ms) |
| GET | `/v1/admin/knowledge-graph` | WORKING (241 ms) |
| GET | `/v1/admin/management-intelligence` | WORKING (10 ms) |
| GET | `/v1/admin/peer-intelligence` | WORKING (961 ms) |
| GET | `/v1/admin/portfolio-intelligence` | WORKING (7 ms) |
| GET | `/v1/admin/regression` | WORKING (3827 ms) |
| GET | `/v1/admin/simulation-lab` | WORKING (19 ms) |

### `ail`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ail/analyse` | WORKING — needs query param |
| GET | `/v1/ail/dashboard` | WORKING (5 ms) |
| GET | `/v1/ail/health` | WORKING (4 ms) |
| POST | `/v1/ail/monitor/run` | not probed |

### `aip`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/aip/attribution` | WORKING (2 ms) |
| GET | `/v1/aip/calibration` | WORKING (2 ms) |
| GET | `/v1/aip/contribution` | WORKING (315 ms) |
| GET | `/v1/aip/dashboard` | WORKING (3 ms) |
| POST | `/v1/aip/experiment` | not probed |
| GET | `/v1/aip/experiments` | WORKING (2 ms) |
| GET | `/v1/aip/experiments/{experiment_id}` | not probed |
| GET | `/v1/aip/health` | WORKING (2 ms) |
| GET | `/v1/aip/house-view-evolution/{ticker}` | not probed |
| GET | `/v1/aip/promotion` | WORKING (2 ms) |
| POST | `/v1/aip/quality` | not probed |
| GET | `/v1/aip/roadmap` | WORKING (2 ms) |
| GET | `/v1/aip/weights` | WORKING (2 ms) |
| POST | `/v1/aip/weights` | not probed |

### `alternative-data`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/alternative-data/beneficiaries/{dataset}` | not probed |
| GET | `/v1/alternative-data/company/{ticker}` | not probed |
| GET | `/v1/alternative-data/dashboard` | WORKING (179 ms) |
| GET | `/v1/alternative-data/dataset/{name}` | not probed |
| GET | `/v1/alternative-data/health` | WORKING (4 ms) |
| GET | `/v1/alternative-data/industry/{industry}` | not probed |
| GET | `/v1/alternative-data/registry` | WORKING (5 ms) |
| GET | `/v1/alternative-data/replay` | WORKING — needs query param |
| POST | `/v1/alternative-data/run` | not probed |
| GET | `/v1/alternative-data/search` | WORKING (5 ms) |
| GET | `/v1/alternative-data/trends` | WORKING (6 ms) |

### `analyst-router`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/analyst-router/constitution` | WORKING (7 ms) |
| GET | `/v1/analyst-router/dashboard` | WORKING (67 ms) |
| POST | `/v1/analyst-router/diagnostics` | not probed |
| GET | `/v1/analyst-router/health` | WORKING (4 ms) |
| GET | `/v1/analyst-router/quality-gates` | WORKING (54 ms) |
| POST | `/v1/analyst-router/route` | not probed |

### `answer-construction`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/answer-construction/health` | WORKING (27 ms) |

### `aoi`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/aoi/companies` | WORKING (5 ms) |
| GET | `/v1/aoi/company/{key}` | not probed |
| GET | `/v1/aoi/connectors` | WORKING (3 ms) |
| GET | `/v1/aoi/consult` | WORKING — needs query param |
| GET | `/v1/aoi/dashboard` | WORKING (2 ms) |
| GET | `/v1/aoi/gaps` | WORKING (2 ms) |
| GET | `/v1/aoi/health` | WORKING (2 ms) |
| GET | `/v1/aoi/learning` | WORKING (2 ms) |
| POST | `/v1/aoi/registry/seed` | not probed |
| POST | `/v1/aoi/run` | not probed |
| GET | `/v1/aoi/scheduler` | WORKING (2 ms) |
| GET | `/v1/aoi/search` | WORKING — needs query param |

### `ask`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ask/context` | WORKING — needs query param |
| GET | `/v1/ask/execution` | WORKING — needs query param |
| GET | `/v1/ask/pipeline` | WORKING (26 ms) |
| GET | `/v1/ask/quality-gates` | WORKING (6132 ms) |
| GET | `/v1/ask/replay` | WORKING — needs query param |
| GET | `/v1/ask/telemetry` | WORKING (6 ms) |

### `aws`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/aws/company/{ticker}` | not probed |
| GET | `/v1/aws/copilot` | WORKING (3 ms) |
| GET | `/v1/aws/cre` | WORKING (2 ms) |
| GET | `/v1/aws/dashboard` | WORKING (4 ms) |
| GET | `/v1/aws/health` | WORKING (3 ms) |
| GET | `/v1/aws/knowledge/{entity}` | not probed |
| GET | `/v1/aws/macro` | WORKING (7 ms) |
| GET | `/v1/aws/portfolio` | WORKING (2 ms) |
| GET | `/v1/aws/replay/{as_of}` | not probed |
| GET | `/v1/aws/research` | WORKING (3 ms) |
| GET | `/v1/aws/search` | WORKING — needs query param |
| GET | `/v1/aws/sector/{sector_id}` | not probed |
| GET | `/v1/aws/theme/{theme_id}` | not probed |

### `belief-engine`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/belief-engine/constitution` | WORKING (12 ms) |
| GET | `/v1/belief-engine/dashboard` | WORKING (320 ms) |
| POST | `/v1/belief-engine/diagnostics` | not probed |
| GET | `/v1/belief-engine/health` | WORKING (4 ms) |
| POST | `/v1/belief-engine/plan` | not probed |
| GET | `/v1/belief-engine/quality-gates` | WORKING (321 ms) |

### `cae`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/cae/cache` | WORKING (3 ms) |
| POST | `/v1/cae/cache/clear` | not probed |
| GET | `/v1/cae/context` | WORKING — needs query param |
| GET | `/v1/cae/dashboard` | WORKING (2 ms) |
| GET | `/v1/cae/explain/{package_id}` | not probed |
| GET | `/v1/cae/health` | WORKING (2 ms) |
| GET | `/v1/cae/metrics` | WORKING (3 ms) |
| GET | `/v1/cae/package/{package_id}` | not probed |
| GET | `/v1/cae/query-plan` | WORKING — needs query param |
| GET | `/v1/cae/retrieval` | WORKING — needs query param |
| GET | `/v1/cae/search` | WORKING — needs query param |

### `causal-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/causal-intelligence/analyse` | not probed |
| GET | `/v1/causal-intelligence/company/{ticker}` | not probed |
| GET | `/v1/causal-intelligence/dashboard` | WORKING (83 ms) |
| GET | `/v1/causal-intelligence/event/{event}` | not probed |
| GET | `/v1/causal-intelligence/graph` | WORKING (6 ms) |
| GET | `/v1/causal-intelligence/health` | WORKING (3 ms) |
| GET | `/v1/causal-intelligence/quality-gates` | WORKING (178 ms) |

### `company`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/company/{ticker}/dossier` | not probed |
| GET | `/v1/company/{ticker}/events` | not probed |
| GET | `/v1/company/{ticker}/forecast` | not probed |
| GET | `/v1/company/{ticker}/ledger` | not probed |
| GET | `/v1/company/{ticker}/monitor` | not probed |
| GET | `/v1/company/{ticker}/thesis` | not probed |
| GET | `/v1/company/{ticker}/timeline` | not probed |

### `company-analysis`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/company-analysis/analyse` | not probed |
| GET | `/v1/company-analysis/dashboard` | WORKING (7 ms) |
| GET | `/v1/company-analysis/health` | WORKING (3 ms) |
| GET | `/v1/company-analysis/quality-gates` | WORKING (884 ms) |
| GET | `/v1/company-analysis/report/{ticker}` | not probed |
| GET | `/v1/company-analysis/reports` | WORKING (5 ms) |

### `company-dossier`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/company-dossier` | WORKING (20 ms) |
| GET | `/v1/company-dossier/health` | WORKING (3 ms) |
| GET | `/v1/company-dossier/quality-gates` | SLOW (>25 s) |
| GET | `/v1/company-dossier/{ticker}` | not probed |
| GET | `/v1/company-dossier/{ticker}/coverage` | not probed |
| GET | `/v1/company-dossier/{ticker}/documents` | not probed |
| GET | `/v1/company-dossier/{ticker}/forecast` | not probed |
| GET | `/v1/company-dossier/{ticker}/risk` | not probed |
| GET | `/v1/company-dossier/{ticker}/timeline` | not probed |
| GET | `/v1/company-dossier/{ticker}/valuation` | not probed |

### `company-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/company-intelligence/coverage` | WORKING (8 ms) |
| GET | `/v1/company-intelligence/dashboard` | WORKING (7 ms) |
| GET | `/v1/company-intelligence/health` | WORKING (5 ms) |
| GET | `/v1/company-intelligence/quality` | WORKING (6 ms) |
| POST | `/v1/company-intelligence/run` | not probed |
| GET | `/v1/company-intelligence/search` | WORKING (6 ms) |
| GET | `/v1/company-intelligence/{ticker}` | not probed |

### `company-monitor`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/company-monitor/alerts` | WORKING (11 ms) |
| GET | `/v1/company-monitor/changes` | WORKING (3 ms) |
| GET | `/v1/company-monitor/dashboard` | WORKING (16 ms) |
| GET | `/v1/company-monitor/health` | WORKING (3 ms) |
| GET | `/v1/company-monitor/quality-gates` | WORKING (3 ms) |
| GET | `/v1/company-monitor/reviews` | WORKING (4 ms) |
| POST | `/v1/company-monitor/run` | not probed |
| POST | `/v1/company-monitor/run-universe` | not probed |

### `company-timeline`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/company-timeline/{ticker}` | not probed |

### `context-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/context-intelligence/constitution` | WORKING (3 ms) |
| GET | `/v1/context-intelligence/dashboard` | WORKING (1009 ms) |
| POST | `/v1/context-intelligence/diagnostics` | not probed |
| POST | `/v1/context-intelligence/enrich` | not probed |
| GET | `/v1/context-intelligence/health` | WORKING (6 ms) |
| GET | `/v1/context-intelligence/quality-gates` | WORKING (901 ms) |

### `contradiction-reasoning`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/contradiction-reasoning/health` | WORKING (6 ms) |

### `corporate-events`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/corporate-events/dashboard` | WORKING (1212 ms) |
| GET | `/v1/corporate-events/health` | WORKING (6 ms) |
| POST | `/v1/corporate-events/run` | not probed |
| GET | `/v1/corporate-events/search` | WORKING (231 ms) |
| GET | `/v1/corporate-events/{ticker}` | not probed |

### `cre`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/cre/alerts` | WORKING (2 ms) |
| GET | `/v1/cre/dashboard` | WORKING — no data yet |
| POST | `/v1/cre/evaluate` | not probed |
| GET | `/v1/cre/health` | WORKING (2 ms) |
| GET | `/v1/cre/promotion` | WORKING — no data yet |
| GET | `/v1/cre/scorecards` | WORKING (2 ms) |
| GET | `/v1/cre/scorecards/{engine}` | not probed |

### `debate-engine`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/debate-engine/constitution` | WORKING (30 ms) |
| GET | `/v1/debate-engine/dashboard` | WORKING (745 ms) |
| POST | `/v1/debate-engine/diagnostics` | not probed |
| GET | `/v1/debate-engine/health` | WORKING (5 ms) |
| POST | `/v1/debate-engine/plan` | not probed |
| GET | `/v1/debate-engine/quality-gates` | WORKING (708 ms) |

### `decision-engine-v2`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/decision-engine-v2/analyse` | not probed |
| GET | `/v1/decision-engine-v2/audit/{audit_id}` | not probed |
| GET | `/v1/decision-engine-v2/company/{ticker}` | not probed |
| GET | `/v1/decision-engine-v2/dashboard` | WORKING (436 ms) |
| GET | `/v1/decision-engine-v2/freeze-review` | WORKING (4 ms) |
| GET | `/v1/decision-engine-v2/health` | WORKING (4 ms) |
| GET | `/v1/decision-engine-v2/monitoring/{ticker}` | not probed |
| GET | `/v1/decision-engine-v2/quality-gates` | WORKING (406 ms) |

### `decision-quality`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/decision-quality/calibration` | WORKING (5 ms) |
| GET | `/v1/decision-quality/dashboard` | WORKING (550 ms) |
| GET | `/v1/decision-quality/decisions` | WORKING (12 ms) |
| GET | `/v1/decision-quality/decisions/{decision_id}` | not probed |
| GET | `/v1/decision-quality/hall` | WORKING (4 ms) |
| GET | `/v1/decision-quality/health` | WORKING (3 ms) |
| GET | `/v1/decision-quality/missing-outcome` | WORKING (5 ms) |
| GET | `/v1/decision-quality/quality-gates` | WORKING (510 ms) |
| GET | `/v1/decision-quality/replay/{decision_id}` | not probed |
| POST | `/v1/decision-quality/run` | not probed |
| GET | `/v1/decision-quality/scorecards/framework` | WORKING (4 ms) |
| GET | `/v1/decision-quality/scorecards/macro` | WORKING (4 ms) |
| GET | `/v1/decision-quality/scorecards/portfolio` | WORKING (4 ms) |
| GET | `/v1/decision-quality/scorecards/sector` | WORKING (3 ms) |

### `decision-readiness`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/decision-readiness/constitution` | WORKING (38 ms) |
| GET | `/v1/decision-readiness/dashboard` | WORKING (2444 ms) |
| POST | `/v1/decision-readiness/diagnostics` | not probed |
| GET | `/v1/decision-readiness/health` | WORKING (4 ms) |
| POST | `/v1/decision-readiness/plan` | not probed |
| GET | `/v1/decision-readiness/quality-gates` | WORKING (2750 ms) |

### `documents`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/documents/company/{ticker}` | not probed |
| GET | `/v1/documents/dashboard` | WORKING (7 ms) |
| GET | `/v1/documents/health` | WORKING (5 ms) |
| GET | `/v1/documents/replay` | WORKING (5 ms) |
| GET | `/v1/documents/report/{doc_id}` | not probed |
| POST | `/v1/documents/run` | not probed |
| GET | `/v1/documents/search` | WORKING (5 ms) |

### `dvc`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/dvc/company/{ticker}` | not probed |
| GET | `/v1/dvc/conflicts` | WORKING (4 ms) |
| GET | `/v1/dvc/dashboard` | WORKING (5 ms) |
| POST | `/v1/dvc/enrich/{ticker}` | not probed |
| GET | `/v1/dvc/health` | WORKING (4 ms) |
| GET | `/v1/dvc/metrics` | WORKING (4 ms) |
| GET | `/v1/dvc/quality-gates` | WORKING (4 ms) |
| POST | `/v1/dvc/validate/{ticker}` | not probed |

### `e01`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e01/health` | WORKING (2 ms) |
| GET | `/v1/e01/history` | WORKING (2 ms) |
| GET | `/v1/e01/state` | WORKING — no data yet |

### `e02`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e02/exposure/{symbol}` | not probed |
| GET | `/v1/e02/health` | WORKING (2 ms) |
| GET | `/v1/e02/history/{symbol}` | not probed |

### `e03`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e03/alpha/{symbol}` | not probed |
| GET | `/v1/e03/health` | WORKING (2 ms) |
| GET | `/v1/e03/history/{symbol}` | not probed |
| GET | `/v1/e03/parity` | WORKING — no data yet |

### `e04`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e04/health` | WORKING (2 ms) |
| GET | `/v1/e04/history/{pair}` | not probed |
| GET | `/v1/e04/state/{pair}` | not probed |

### `e05`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e05/events/{symbol}` | not probed |
| GET | `/v1/e05/health` | WORKING (2 ms) |
| GET | `/v1/e05/history/{symbol}` | not probed |

### `e08`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e08/health` | WORKING (2 ms) |
| GET | `/v1/e08/history/{symbol}` | not probed |
| GET | `/v1/e08/state/{symbol}` | not probed |

### `e09`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e09/health` | WORKING (2 ms) |
| GET | `/v1/e09/history/{symbol}` | not probed |
| GET | `/v1/e09/state/{symbol}` | not probed |

### `e10`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e10/health` | WORKING (2 ms) |
| GET | `/v1/e10/history` | WORKING (2 ms) |
| GET | `/v1/e10/portfolio` | WORKING — no data yet |

### `e11`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e11/health` | WORKING (2 ms) |
| GET | `/v1/e11/history/{symbol}` | not probed |
| GET | `/v1/e11/sentiment/{symbol}` | not probed |
| GET | `/v1/e11/state/{symbol}` | not probed |

### `e13`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e13/fundamental/{symbol}` | not probed |
| GET | `/v1/e13/health` | WORKING (2 ms) |
| GET | `/v1/e13/history/{symbol}` | not probed |

### `e14`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/e14/health` | WORKING (2 ms) |
| GET | `/v1/e14/history` | WORKING (2 ms) |
| GET | `/v1/e14/state` | WORKING — no data yet |

### `ecp`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/ecp/complete` | not probed |
| GET | `/v1/ecp/dashboard` | WORKING (38 ms) |
| GET | `/v1/ecp/health` | WORKING (4 ms) |
| GET | `/v1/ecp/quality-gates` | WORKING (4 ms) |
| GET | `/v1/ecp/report/{ticker}` | not probed |
| GET | `/v1/ecp/reports` | WORKING (4 ms) |

### `editorial`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/editorial/health` | WORKING (5 ms) |

### `entity-resolution`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/entity-resolution/constitution` | WORKING (3 ms) |
| GET | `/v1/entity-resolution/dashboard` | WORKING (4499 ms) |
| POST | `/v1/entity-resolution/diagnostics` | not probed |
| GET | `/v1/entity-resolution/health` | WORKING (4 ms) |
| GET | `/v1/entity-resolution/quality-gates` | WORKING (3830 ms) |
| POST | `/v1/entity-resolution/resolve` | not probed |

### `eval`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/eval/predictions` | not probed |
| GET | `/v1/eval/predictions/pending` | WORKING — needs auth token |

### `eve`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/eve/audit` | WORKING (3 ms) |
| GET | `/v1/eve/company/{key}` | not probed |
| GET | `/v1/eve/conflicts` | WORKING (2 ms) |
| GET | `/v1/eve/consult` | WORKING — needs query param |
| GET | `/v1/eve/dashboard` | WORKING (3 ms) |
| GET | `/v1/eve/evidence` | WORKING (2 ms) |
| GET | `/v1/eve/evidence/{evidence_id}` | not probed |
| GET | `/v1/eve/health` | WORKING (2 ms) |
| GET | `/v1/eve/search` | WORKING — needs query param |
| GET | `/v1/eve/source` | WORKING (2 ms) |
| GET | `/v1/eve/timeline` | WORKING (2 ms) |
| GET | `/v1/eve/trust` | WORKING (2 ms) |
| GET | `/v1/eve/verification` | WORKING (2 ms) |
| POST | `/v1/eve/verification/run` | not probed |

### `event`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/event/{event_id}` | not probed |

### `events`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/events/critical` | WORKING (112 ms) |
| GET | `/v1/events/today` | WORKING (122 ms) |

### `evidence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/evidence/company/{ticker}` | not probed |
| GET | `/v1/evidence/dashboard` | WORKING (5 ms) |
| GET | `/v1/evidence/document/{doc_id}` | not probed |
| GET | `/v1/evidence/graph` | WORKING (4 ms) |
| GET | `/v1/evidence/health` | WORKING (4 ms) |
| GET | `/v1/evidence/replay` | WORKING — needs query param |
| GET | `/v1/evidence/search` | WORKING — needs query param |
| GET | `/v1/evidence/{evidence_id}` | not probed |

### `expectations`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/expectations/company/{ticker}` | not probed |
| GET | `/v1/expectations/dashboard` | WORKING (5 ms) |
| GET | `/v1/expectations/gap/{ticker}` | not probed |
| GET | `/v1/expectations/health` | WORKING (4 ms) |
| GET | `/v1/expectations/narratives` | WORKING (4 ms) |
| GET | `/v1/expectations/phase2-consensus` | WORKING (4 ms) |
| GET | `/v1/expectations/registry` | WORKING (6 ms) |
| GET | `/v1/expectations/replay` | WORKING — needs query param |
| GET | `/v1/expectations/revisions` | WORKING (5 ms) |
| POST | `/v1/expectations/run` | not probed |
| GET | `/v1/expectations/search` | WORKING (6 ms) |
| GET | `/v1/expectations/surprises` | WORKING (5 ms) |

### `faa`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/faa/acquire` | not probed |
| GET | `/v1/faa/connectors` | WORKING (3 ms) |
| GET | `/v1/faa/consult` | WORKING — needs query param |
| GET | `/v1/faa/dashboard` | WORKING (3 ms) |
| GET | `/v1/faa/discover` | WORKING — needs query param |
| GET | `/v1/faa/health` | WORKING (3 ms) |
| POST | `/v1/faa/jobs` | not probed |
| GET | `/v1/faa/scheduler` | WORKING (2 ms) |

### `features`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/features` | WORKING — needs auth token |
| GET | `/v1/features/dependency-order` | WORKING — needs auth token |
| GET | `/v1/features/health` | WORKING (4 ms) |
| POST | `/v1/features/register` | not probed |
| GET | `/v1/features/schedule/frequencies` | WORKING — needs auth token |
| GET | `/v1/features/schedule/plan` | WORKING — needs auth token |
| GET | `/v1/features/{feature_id}` | not probed |
| GET | `/v1/features/{feature_id}/value` | not probed |

### `filing-diff`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/filing-diff/analyse` | not probed |
| GET | `/v1/filing-diff/changes/{ticker}` | not probed |
| GET | `/v1/filing-diff/company/{ticker}` | not probed |
| GET | `/v1/filing-diff/dashboard` | WORKING (3 ms) |
| GET | `/v1/filing-diff/health` | WORKING (3 ms) |
| GET | `/v1/filing-diff/quality-gates` | WORKING (6 ms) |
| GET | `/v1/filing-diff/timeline/{ticker}` | not probed |

### `filing-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/filing-intelligence/analyse` | not probed |
| GET | `/v1/filing-intelligence/company/{ticker}` | not probed |
| GET | `/v1/filing-intelligence/dashboard` | WORKING (3 ms) |
| GET | `/v1/filing-intelligence/evidence/{ticker}` | not probed |
| GET | `/v1/filing-intelligence/health` | WORKING (2 ms) |
| GET | `/v1/filing-intelligence/history/{ticker}` | not probed |
| POST | `/v1/filing-intelligence/ingest` | not probed |
| GET | `/v1/filing-intelligence/quality-gates` | WORKING (8 ms) |
| GET | `/v1/filing-intelligence/timeline/{ticker}` | not probed |

### `fiml`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/fiml/analyse/{domain}` | not probed |
| POST | `/v1/fiml/bundle` | not probed |
| POST | `/v1/fiml/compare/{domain}` | not probed |
| POST | `/v1/fiml/consumer/{engine}` | not probed |
| GET | `/v1/fiml/dashboard` | WORKING (10 ms) |
| POST | `/v1/fiml/explain/{domain}` | not probed |
| GET | `/v1/fiml/graph` | WORKING (3 ms) |
| GET | `/v1/fiml/health` | WORKING (2 ms) |
| GET | `/v1/fiml/industries` | WORKING (3 ms) |
| GET | `/v1/fiml/metrics` | WORKING (3 ms) |
| GET | `/v1/fiml/models` | WORKING (2 ms) |
| POST | `/v1/fiml/monitor/{domain}` | not probed |
| POST | `/v1/fiml/relationships/{domain}` | not probed |
| POST | `/v1/fiml/score/{domain}` | not probed |
| GET | `/v1/fiml/search` | WORKING — needs query param |

### `fle`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/fle/accuracy` | WORKING (2 ms) |
| POST | `/v1/fle/batch` | not probed |
| GET | `/v1/fle/calibration` | WORKING (3 ms) |
| GET | `/v1/fle/company/{key}` | not probed |
| GET | `/v1/fle/compare/{forecast_id}` | not probed |
| GET | `/v1/fle/consult` | WORKING — needs query param |
| GET | `/v1/fle/dashboard` | WORKING (2 ms) |
| GET | `/v1/fle/forecast` | WORKING (2 ms) |
| POST | `/v1/fle/forecast` | not probed |
| GET | `/v1/fle/forecast/{forecast_id}` | not probed |
| POST | `/v1/fle/forecast/{forecast_id}/resolve` | not probed |
| POST | `/v1/fle/forecast/{forecast_id}/version` | not probed |
| POST | `/v1/fle/generate` | not probed |
| GET | `/v1/fle/health` | WORKING (2 ms) |
| GET | `/v1/fle/history` | WORKING (2 ms) |
| POST | `/v1/fle/jobs` | not probed |
| GET | `/v1/fle/learning` | WORKING (2 ms) |
| GET | `/v1/fle/outcomes` | WORKING (2 ms) |
| GET | `/v1/fle/scenarios/{forecast_id}` | not probed |
| GET | `/v1/fle/search` | WORKING — needs query param |

### `forecast`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/forecast/analyse` | not probed |
| GET | `/v1/forecast/catalysts/{ticker}` | not probed |
| GET | `/v1/forecast/company/{ticker}` | not probed |
| GET | `/v1/forecast/dashboard` | WORKING (74 ms) |
| GET | `/v1/forecast/health` | WORKING (3 ms) |
| GET | `/v1/forecast/quality-gates` | WORKING (77 ms) |
| GET | `/v1/forecast/scenarios/{ticker}` | not probed |

### `framework-selection`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/framework-selection/dashboard` | WORKING (5 ms) |
| GET | `/v1/framework-selection/framework/{framework_id}` | not probed |
| GET | `/v1/framework-selection/health` | WORKING (4 ms) |
| GET | `/v1/framework-selection/history` | WORKING (3 ms) |
| GET | `/v1/framework-selection/registry` | WORKING (5 ms) |
| GET | `/v1/framework-selection/select` | WORKING — needs query param |

### `fre`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/fre/company/{key}` | not probed |
| GET | `/v1/fre/consult` | WORKING — needs query param |
| GET | `/v1/fre/dashboard` | WORKING (3 ms) |
| GET | `/v1/fre/document/{document_id}` | not probed |
| GET | `/v1/fre/evidence` | WORKING (2 ms) |
| GET | `/v1/fre/graph` | WORKING (3 ms) |
| GET | `/v1/fre/health` | WORKING (3 ms) |
| POST | `/v1/fre/ingest` | not probed |
| POST | `/v1/fre/jobs` | not probed |
| GET | `/v1/fre/news` | WORKING (2 ms) |
| GET | `/v1/fre/query` | WORKING — needs query param |
| GET | `/v1/fre/scheduler` | WORKING (2 ms) |
| GET | `/v1/fre/search` | WORKING — needs query param |
| GET | `/v1/fre/timeline` | WORKING (2 ms) |

### `government`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/government/budget` | WORKING (4 ms) |
| GET | `/v1/government/dashboard` | WORKING (7 ms) |
| GET | `/v1/government/gst` | WORKING (5 ms) |
| GET | `/v1/government/health` | WORKING (4 ms) |
| GET | `/v1/government/pli` | WORKING (5 ms) |
| GET | `/v1/government/policies` | WORKING (8 ms) |
| GET | `/v1/government/policy/{policy_id}` | not probed |
| GET | `/v1/government/rbi` | WORKING (4 ms) |
| POST | `/v1/government/run` | not probed |
| GET | `/v1/government/search` | WORKING (6 ms) |
| GET | `/v1/government/sebi` | WORKING (4 ms) |
| GET | `/v1/government/timeline` | WORKING (7 ms) |
| GET | `/v1/government/trade` | WORKING (4 ms) |

### `health`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/health` | WORKING (2 ms) |

### `hypothesis-engine`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/hypothesis-engine/constitution` | WORKING (3 ms) |
| GET | `/v1/hypothesis-engine/dashboard` | WORKING (3206 ms) |
| POST | `/v1/hypothesis-engine/diagnostics` | not probed |
| GET | `/v1/hypothesis-engine/health` | WORKING (5 ms) |
| POST | `/v1/hypothesis-engine/plan` | not probed |
| GET | `/v1/hypothesis-engine/quality-gates` | WORKING (2770 ms) |

### `hypothesis-testing`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/hypothesis-testing/constitution` | WORKING (5 ms) |
| GET | `/v1/hypothesis-testing/dashboard` | WORKING (1300 ms) |
| POST | `/v1/hypothesis-testing/diagnostics` | not probed |
| GET | `/v1/hypothesis-testing/health` | WORKING (5 ms) |
| POST | `/v1/hypothesis-testing/plan` | not probed |
| GET | `/v1/hypothesis-testing/quality-gates` | WORKING (1281 ms) |

### `ib`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ib/dashboard` | WORKING (4 ms) |
| GET | `/v1/ib/dead-letter` | WORKING (3 ms) |
| POST | `/v1/ib/dead-letter/{dlq_id}/resolve` | not probed |
| POST | `/v1/ib/demo-chain` | not probed |
| GET | `/v1/ib/events` | WORKING (3 ms) |
| GET | `/v1/ib/health` | WORKING (2 ms) |
| GET | `/v1/ib/history` | WORKING (2 ms) |
| GET | `/v1/ib/metrics` | WORKING (3 ms) |
| POST | `/v1/ib/publish` | not probed |
| POST | `/v1/ib/replay` | not probed |
| GET | `/v1/ib/schema` | WORKING (3 ms) |
| GET | `/v1/ib/subscriptions` | WORKING (3 ms) |
| POST | `/v1/ib/subscriptions` | not probed |
| GET | `/v1/ib/traces` | WORKING (2 ms) |

### `iie`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/iie/analyse` | not probed |
| POST | `/v1/iie/batch` | not probed |
| GET | `/v1/iie/catalysts` | WORKING (2 ms) |
| GET | `/v1/iie/company/{key}` | not probed |
| GET | `/v1/iie/compare` | WORKING — needs query param |
| GET | `/v1/iie/consult` | WORKING — needs query param |
| GET | `/v1/iie/dashboard` | WORKING (4 ms) |
| GET | `/v1/iie/dna/{key}` | not probed |
| GET | `/v1/iie/evolution` | WORKING (3 ms) |
| GET | `/v1/iie/health` | WORKING (3 ms) |
| GET | `/v1/iie/macro` | WORKING — needs query param |
| GET | `/v1/iie/monitor/{key}` | not probed |
| GET | `/v1/iie/opportunities` | WORKING (2 ms) |
| GET | `/v1/iie/risks` | WORKING (2 ms) |
| GET | `/v1/iie/scenario/{key}` | not probed |
| GET | `/v1/iie/search` | WORKING — needs query param |
| GET | `/v1/iie/sector` | WORKING (3 ms) |
| GET | `/v1/iie/sector/{sector_id}` | not probed |
| GET | `/v1/iie/theme` | WORKING (3 ms) |
| GET | `/v1/iie/theme/{theme_id}` | not probed |
| GET | `/v1/iie/thesis/{key}` | not probed |

### `ilm`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ilm/committee/{ticker}` | not probed |
| GET | `/v1/ilm/company/{ticker}` | not probed |
| GET | `/v1/ilm/dashboard` | WORKING (6 ms) |
| GET | `/v1/ilm/forecast/{ticker}` | not probed |
| GET | `/v1/ilm/health` | WORKING (3 ms) |
| POST | `/v1/ilm/learning/update` | not probed |
| GET | `/v1/ilm/portfolio/{portfolio_id}` | not probed |
| GET | `/v1/ilm/quality-gates` | WORKING (7 ms) |
| GET | `/v1/ilm/thesis/{ticker}` | not probed |

### `industry`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/industry/accounting` | WORKING — needs query param |
| GET | `/v1/industry/company/{ticker}` | not probed |
| GET | `/v1/industry/cycles` | WORKING — needs query param |
| GET | `/v1/industry/dashboard` | WORKING (182 ms) |
| GET | `/v1/industry/health` | WORKING (4 ms) |
| GET | `/v1/industry/kpis` | WORKING — needs query param |
| GET | `/v1/industry/playbook` | WORKING — needs query param |
| POST | `/v1/industry/run` | not probed |
| GET | `/v1/industry/search` | WORKING (25 ms) |
| GET | `/v1/industry/valuation` | WORKING — needs query param |
| GET | `/v1/industry/value-chain` | WORKING — needs query param |
| GET | `/v1/industry/{name}` | not probed |

### `institutional-analog-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-analog-intelligence/audits` | WORKING (4 ms) |
| GET | `/v1/institutional-analog-intelligence/catalog` | WORKING (5 ms) |
| GET | `/v1/institutional-analog-intelligence/dashboard` | WORKING (4 ms) |
| GET | `/v1/institutional-analog-intelligence/health` | WORKING (4 ms) |
| GET | `/v1/institutional-analog-intelligence/memory/{memory_id}` | not probed |
| GET | `/v1/institutional-analog-intelligence/retrieve` | WORKING — needs query param |

### `institutional-analysts`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-analysts/health` | WORKING (4 ms) |
| GET | `/v1/institutional-analysts/quality-gates` | WORKING (3 ms) |

### `institutional-communication`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-communication/dashboard` | WORKING (4 ms) |
| GET | `/v1/institutional-communication/health` | WORKING (3 ms) |
| GET | `/v1/institutional-communication/history` | WORKING (3 ms) |

### `institutional-evaluation-lab`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-evaluation-lab/catalog` | WORKING (16 ms) |
| GET | `/v1/institutional-evaluation-lab/dashboard` | WORKING (4 ms) |
| GET | `/v1/institutional-evaluation-lab/health` | WORKING (4 ms) |
| GET | `/v1/institutional-evaluation-lab/history` | WORKING (4 ms) |
| GET | `/v1/institutional-evaluation-lab/nightly` | WORKING (8109 ms) |
| GET | `/v1/institutional-evaluation-lab/question/{question_id}` | not probed |
| GET | `/v1/institutional-evaluation-lab/run` | WORKING (205 ms) |

### `institutional-evidence-graph`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-evidence-graph/build` | WORKING — needs query param |
| GET | `/v1/institutional-evidence-graph/company/{ticker}` | not probed |
| GET | `/v1/institutional-evidence-graph/dashboard` | WORKING (4 ms) |
| GET | `/v1/institutional-evidence-graph/health` | WORKING (5 ms) |
| GET | `/v1/institutional-evidence-graph/history` | WORKING (3 ms) |

### `institutional-knowledge`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-knowledge/company/{ticker}` | not probed |
| GET | `/v1/institutional-knowledge/dashboard` | WORKING (5459 ms) |
| GET | `/v1/institutional-knowledge/health` | WORKING (6 ms) |
| POST | `/v1/institutional-knowledge/run` | not probed |

### `institutional-playbooks`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-playbooks/dashboard` | WORKING (4 ms) |
| GET | `/v1/institutional-playbooks/health` | WORKING (3 ms) |
| GET | `/v1/institutional-playbooks/history` | WORKING (3 ms) |
| GET | `/v1/institutional-playbooks/playbook/{playbook_id}` | not probed |
| GET | `/v1/institutional-playbooks/registry` | WORKING (4 ms) |
| GET | `/v1/institutional-playbooks/select` | WORKING — needs query param |

### `institutional-reasoning`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/institutional-reasoning/adversarial` | WORKING (360 ms) |
| GET | `/v1/institutional-reasoning/baselines` | WORKING (4 ms) |
| GET | `/v1/institutional-reasoning/evidence/{ticker}` | not probed |
| GET | `/v1/institutional-reasoning/graphs` | WORKING — needs query param |
| GET | `/v1/institutional-reasoning/health` | WORKING (4 ms) |
| GET | `/v1/institutional-reasoning/observability` | WORKING (3 ms) |
| GET | `/v1/institutional-reasoning/portfolio/{ticker}` | not probed |
| GET | `/v1/institutional-reasoning/stack` | WORKING (70 ms) |
| GET | `/v1/institutional-reasoning/universe` | WORKING (4 ms) |

### `institutional-stack`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/institutional-stack/analyse` | not probed |
| POST | `/v1/institutional-stack/bootstrap` | not probed |
| GET | `/v1/institutional-stack/company/{ticker}` | not probed |
| GET | `/v1/institutional-stack/dashboard` | WORKING (1254 ms) |
| GET | `/v1/institutional-stack/health` | WORKING (4 ms) |
| POST | `/v1/institutional-stack/ingest` | not probed |
| GET | `/v1/institutional-stack/quality-gates` | WORKING (708 ms) |

### `investment-committee`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/investment-committee/health` | WORKING (20 ms) |
| GET | `/v1/investment-committee/quality-gates` | WORKING (4 ms) |
| POST | `/v1/investment-committee/record-actuals` | not probed |
| GET | `/v1/investment-committee/timeline/{ticker}` | not probed |

### `investment-office`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/investment-office/dashboard` | WORKING (53 ms) |
| GET | `/v1/investment-office/health` | WORKING (3 ms) |
| POST | `/v1/investment-office/package` | not probed |
| GET | `/v1/investment-office/quality-gates` | WORKING (13 ms) |

### `ioc`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ioc/alerts` | WORKING (3 ms) |
| GET | `/v1/ioc/dashboard` | WORKING (5 ms) |
| GET | `/v1/ioc/health` | WORKING (3 ms) |
| GET | `/v1/ioc/providers` | WORKING (3 ms) |
| GET | `/v1/ioc/readiness` | WORKING (3 ms) |
| GET | `/v1/ioc/report` | WORKING (5 ms) |

### `irp`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/irp/health` | WORKING (3 ms) |
| GET | `/v1/irp/learning` | WORKING (3 ms) |
| POST | `/v1/irp/run` | not probed |

### `kc`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/kc/consult` | WORKING — needs query param |
| GET | `/v1/kc/dashboard` | WORKING (10 ms) |
| GET | `/v1/kc/gaps` | WORKING (6 ms) |
| GET | `/v1/kc/health` | WORKING (3 ms) |
| GET | `/v1/kc/learning` | WORKING (2 ms) |
| GET | `/v1/kc/metrics` | WORKING (3 ms) |
| POST | `/v1/kc/populate` | not probed |
| GET | `/v1/kc/quality` | WORKING (4 ms) |
| POST | `/v1/kc/universe` | not probed |

### `kf`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/kf/companies` | WORKING (2 ms) |
| GET | `/v1/kf/company/{ticker}` | not probed |
| GET | `/v1/kf/coverage` | WORKING (2 ms) |
| GET | `/v1/kf/extracts` | WORKING (2 ms) |
| GET | `/v1/kf/health` | WORKING (2 ms) |
| GET | `/v1/kf/macro/{macro_id}` | not probed |
| GET | `/v1/kf/macros` | WORKING (2 ms) |
| GET | `/v1/kf/predictions` | WORKING (2 ms) |
| POST | `/v1/kf/rebuild` | not probed |
| GET | `/v1/kf/search` | WORKING — needs query param |
| GET | `/v1/kf/sector/{sector_id}` | not probed |
| GET | `/v1/kf/sectors` | WORKING (2 ms) |
| POST | `/v1/kf/seed` | not probed |
| GET | `/v1/kf/theme/{theme_id}` | not probed |
| GET | `/v1/kf/themes` | WORKING (2 ms) |

### `kip`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/kip/client-search` | not probed |
| GET | `/v1/kip/company-dossier/{ticker}` | not probed |
| GET | `/v1/kip/company/{ticker}` | not probed |
| GET | `/v1/kip/document/{document_id}` | not probed |
| GET | `/v1/kip/graph/{entity}` | not probed |
| GET | `/v1/kip/health` | WORKING (2 ms) |
| GET | `/v1/kip/house-view/{ticker}` | not probed |
| POST | `/v1/kip/ingest` | not probed |
| POST | `/v1/kip/ingest/agi` | not probed |
| POST | `/v1/kip/ingest/broker` | not probed |
| POST | `/v1/kip/ingest/internal` | not probed |
| POST | `/v1/kip/ingest/newsletter` | not probed |
| GET | `/v1/kip/integrity` | WORKING (2 ms) |
| POST | `/v1/kip/predictions/evaluate` | not probed |
| GET | `/v1/kip/predictions/{ticker}` | not probed |
| GET | `/v1/kip/rag` | WORKING — needs query param |
| GET | `/v1/kip/research-context` | WORKING — needs query param |
| GET | `/v1/kip/research-history/{ticker}` | not probed |
| GET | `/v1/kip/search` | WORKING — needs query param |
| GET | `/v1/kip/similar/{document_id}` | not probed |
| POST | `/v1/kip/snapshot/reload` | not probed |
| POST | `/v1/kip/snapshot/save` | not probed |
| GET | `/v1/kip/theme/{theme_id}` | not probed |
| GET | `/v1/kip/timeline/{ticker}` | not probed |
| GET | `/v1/kip/verify/{document_id}` | not probed |

### `knowledge-factory`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/knowledge-factory/company/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/coverage` | WORKING (5760 ms) |
| GET | `/v1/knowledge-factory/daily-health` | WORKING (3817 ms) |
| GET | `/v1/knowledge-factory/dashboard` | WORKING (5641 ms) |
| GET | `/v1/knowledge-factory/decision-coverage` | WORKING (44 ms) |
| GET | `/v1/knowledge-factory/dimensions` | WORKING (150 ms) |
| GET | `/v1/knowledge-factory/evidence/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/health` | WORKING (6 ms) |
| GET | `/v1/knowledge-factory/historical-depth` | WORKING (133 ms) |
| GET | `/v1/knowledge-factory/historical-depth/as-of/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/historical-depth/compare/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/historical-depth/query/{ticker}/crisis-drawdown` | not probed |
| GET | `/v1/knowledge-factory/historical-depth/query/{ticker}/pe-percentile` | not probed |
| GET | `/v1/knowledge-factory/historical-depth/query/{ticker}/rate-hiking-cycles` | not probed |
| GET | `/v1/knowledge-factory/historical-depth/query/{ticker}/valuation/{year}` | not probed |
| POST | `/v1/knowledge-factory/historical-depth/run` | not probed |
| GET | `/v1/knowledge-factory/institutional-depth` | WORKING (1125 ms) |
| GET | `/v1/knowledge-factory/institutional-depth/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/macro-intelligence` | WORKING (25 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/playbook/{regime}` | not probed |
| GET | `/v1/knowledge-factory/macro-intelligence/query/falling-rates` | WORKING (5 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/oil-shock` | WORKING (5 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/regime` | WORKING (5 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/replay/2008` | WORKING (5 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/replay/covid` | WORKING (5 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/replay/{as_of}` | not probed |
| GET | `/v1/knowledge-factory/macro-intelligence/query/similar` | WORKING (8 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/unavailable` | WORKING (4 ms) |
| GET | `/v1/knowledge-factory/macro-intelligence/query/usd-it` | WORKING (5 ms) |
| POST | `/v1/knowledge-factory/macro-intelligence/run` | not probed |
| GET | `/v1/knowledge-factory/macro-intelligence/{macro_id}` | not probed |
| GET | `/v1/knowledge-factory/quality-gates` | WORKING (5927 ms) |
| POST | `/v1/knowledge-factory/run-daily` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence` | WORKING (15 ms) |
| GET | `/v1/knowledge-factory/sector-intelligence/query/expensive/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence/query/framework/{ticker}` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence/query/rates-fall` | WORKING (6 ms) |
| GET | `/v1/knowledge-factory/sector-intelligence/query/regime/{regime_id}` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence/query/strongest-roic` | WORKING (4 ms) |
| GET | `/v1/knowledge-factory/sector-intelligence/query/valuation/{sector}/{year}` | not probed |
| POST | `/v1/knowledge-factory/sector-intelligence/run` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence/{sector}` | not probed |
| GET | `/v1/knowledge-factory/sector-intelligence/{sector}/playbook` | not probed |
| GET | `/v1/knowledge-factory/universe-tiers` | WORKING (4 ms) |

### `knowledge-graph`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/knowledge-graph/company/{ticker}` | not probed |
| GET | `/v1/knowledge-graph/dashboard` | WORKING (32 ms) |
| GET | `/v1/knowledge-graph/entity/{entity_id}` | not probed |
| GET | `/v1/knowledge-graph/health` | WORKING (3 ms) |
| GET | `/v1/knowledge-graph/path` | WORKING — needs query param |
| GET | `/v1/knowledge-graph/quality-gates` | WORKING (158 ms) |
| POST | `/v1/knowledge-graph/query` | not probed |
| GET | `/v1/knowledge-graph/relationships/{entity_id}` | not probed |

### `l4`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/l4/health` | WORKING (3 ms) |
| GET | `/v1/l4/history/{symbol}` | not probed |
| GET | `/v1/l4/opinion/{symbol}` | not probed |

### `layer-router`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/layer-router/constitution` | WORKING (4 ms) |
| GET | `/v1/layer-router/dashboard` | WORKING (214 ms) |
| POST | `/v1/layer-router/diagnostics` | not probed |
| GET | `/v1/layer-router/health` | WORKING (3 ms) |
| POST | `/v1/layer-router/plan` | not probed |
| GET | `/v1/layer-router/quality-gates` | WORKING (140 ms) |

### `leo`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/leo/dashboard` | WORKING (20 ms) |
| GET | `/v1/leo/dossier/{ticker}` | not probed |
| GET | `/v1/leo/health` | WORKING (3 ms) |
| POST | `/v1/leo/package` | not probed |
| GET | `/v1/leo/quality-gates` | WORKING (1283 ms) |

### `live-data`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/live-data/collectors` | WORKING (4 ms) |
| GET | `/v1/live-data/dashboard` | WORKING (5 ms) |
| GET | `/v1/live-data/fallback` | WORKING (5 ms) |
| GET | `/v1/live-data/freshness` | WORKING (4 ms) |
| POST | `/v1/live-data/run` | not probed |
| GET | `/v1/live-data/sources` | WORKING (3 ms) |
| GET | `/v1/live-data/status` | WORKING (3 ms) |
| GET | `/v1/live-data/validation` | WORKING (4 ms) |
| GET | `/v1/live-data/verification/certification` | WORKING (5 ms) |
| GET | `/v1/live-data/verification/dashboard` | WORKING (6 ms) |
| GET | `/v1/live-data/verification/probes` | WORKING (10337 ms) |
| GET | `/v1/live-data/verification/report` | WORKING (6 ms) |
| POST | `/v1/live-data/verification/report/generate` | not probed |
| POST | `/v1/live-data/verification/run` | not probed |
| GET | `/v1/live-data/verification/status` | WORKING (5 ms) |
| GET | `/v1/live-data/verification/telemetry` | WORKING (4 ms) |

### `management-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/management-intelligence/analyse` | not probed |
| GET | `/v1/management-intelligence/company/{ticker}` | not probed |
| GET | `/v1/management-intelligence/dashboard` | WORKING (3 ms) |
| GET | `/v1/management-intelligence/guidance/{ticker}` | not probed |
| GET | `/v1/management-intelligence/health` | WORKING (2 ms) |
| GET | `/v1/management-intelligence/history/{ticker}` | not probed |
| GET | `/v1/management-intelligence/quality-gates` | WORKING (6 ms) |

### `market-data`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/market-data/health` | WORKING (3 ms) |

### `mee`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/mee/company/{key}` | not probed |
| GET | `/v1/mee/consult` | WORKING — needs query param |
| POST | `/v1/mee/cycle` | not probed |
| GET | `/v1/mee/dashboard` | WORKING (2 ms) |
| GET | `/v1/mee/events` | WORKING (2 ms) |
| POST | `/v1/mee/events` | not probed |
| GET | `/v1/mee/events/{event_id}` | not probed |
| POST | `/v1/mee/events/{event_id}/verify` | not probed |
| POST | `/v1/mee/events/{event_id}/version` | not probed |
| GET | `/v1/mee/health` | WORKING (2 ms) |
| GET | `/v1/mee/history` | WORKING (2 ms) |
| GET | `/v1/mee/impact/{event_id}` | not probed |
| GET | `/v1/mee/relationships` | WORKING (3 ms) |
| GET | `/v1/mee/search` | WORKING — needs query param |
| GET | `/v1/mee/sector/{sector_id}` | not probed |
| GET | `/v1/mee/similar/{event_id}` | not probed |
| GET | `/v1/mee/theme/{theme_id}` | not probed |
| GET | `/v1/mee/timeline` | WORKING (2 ms) |

### `mission-control`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/mission-control/acknowledge` | not probed |
| GET | `/v1/mission-control/dashboard` | WORKING (12937 ms) |
| GET | `/v1/mission-control/health` | WORKING (4 ms) |
| GET | `/v1/mission-control/quality-gates` | WORKING (5 ms) |
| GET | `/v1/mission-control/report` | WORKING (8 ms) |

### `orch`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/orch/l2/builds` | WORKING — needs auth token |
| GET | `/v1/orch/l2/builds/{build_id}` | not probed |
| POST | `/v1/orch/l2/drain` | not probed |
| GET | `/v1/orch/l2/health` | WORKING (2 ms) |
| POST | `/v1/orch/l2/trigger` | not probed |
| GET | `/v1/orch/status` | WORKING (2 ms) |

### `patch-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/patch-intelligence/health` | WORKING (3 ms) |
| GET | `/v1/patch-intelligence/queue` | WORKING (3 ms) |

### `peer-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/peer-intelligence/analyse` | not probed |
| GET | `/v1/peer-intelligence/company/{ticker}` | not probed |
| GET | `/v1/peer-intelligence/compare` | WORKING (30 ms) |
| GET | `/v1/peer-intelligence/dashboard` | WORKING (12 ms) |
| GET | `/v1/peer-intelligence/health` | WORKING (2 ms) |
| GET | `/v1/peer-intelligence/history/{ticker}` | not probed |
| GET | `/v1/peer-intelligence/quality-gates` | WORKING (761 ms) |
| GET | `/v1/peer-intelligence/rankings` | WORKING (80 ms) |

### `portfolio-intelligence`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/portfolio-intelligence/analyse` | not probed |
| GET | `/v1/portfolio-intelligence/dashboard` | WORKING (5 ms) |
| GET | `/v1/portfolio-intelligence/health` | WORKING (3 ms) |
| GET | `/v1/portfolio-intelligence/health/{portfolio_id}` | not probed |
| GET | `/v1/portfolio-intelligence/portfolio/{portfolio_id}` | not probed |
| GET | `/v1/portfolio-intelligence/quality-gates` | WORKING (4 ms) |
| GET | `/v1/portfolio-intelligence/scenarios/{portfolio_id}` | not probed |

### `prediction`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/prediction/{prediction_id}` | not probed |

### `reasoning-audit`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/reasoning-audit/constitution` | WORKING (7 ms) |
| GET | `/v1/reasoning-audit/dashboard` | WORKING (1687 ms) |
| POST | `/v1/reasoning-audit/diagnostics` | not probed |
| GET | `/v1/reasoning-audit/health` | WORKING (5 ms) |
| POST | `/v1/reasoning-audit/plan` | not probed |
| GET | `/v1/reasoning-audit/quality-gates` | WORKING (1701 ms) |

### `red-team`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/red-team/ecr/health` | WORKING (14 ms) |

### `relationship`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/relationship/commodity/{commodity}` | not probed |
| GET | `/v1/relationship/company/{ticker}` | not probed |
| GET | `/v1/relationship/dashboard` | WORKING (16 ms) |
| GET | `/v1/relationship/health` | WORKING (4 ms) |
| GET | `/v1/relationship/industry/{industry}` | not probed |
| GET | `/v1/relationship/macro/{macro}` | not probed |
| GET | `/v1/relationship/network/{entity}` | not probed |
| GET | `/v1/relationship/path` | WORKING — needs query param |
| GET | `/v1/relationship/policy/{policy}` | not probed |
| GET | `/v1/relationship/registry` | WORKING (3 ms) |
| GET | `/v1/relationship/replay` | WORKING — needs query param |
| POST | `/v1/relationship/run` | not probed |
| GET | `/v1/relationship/search` | WORKING (10 ms) |
| GET | `/v1/relationship/shock/{entity}` | not probed |

### `research`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research/runs` | WORKING — needs auth token |
| POST | `/v1/research/runs` | not probed |
| GET | `/v1/research/runs/{run_id}` | not probed |

### `research-blueprint`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research-blueprint/constitution` | WORKING (3 ms) |
| GET | `/v1/research-blueprint/dashboard` | WORKING (50 ms) |
| POST | `/v1/research-blueprint/diagnostics` | not probed |
| POST | `/v1/research-blueprint/enrich` | not probed |
| GET | `/v1/research-blueprint/health` | WORKING (4 ms) |
| POST | `/v1/research-blueprint/plan` | not probed |
| GET | `/v1/research-blueprint/quality-gates` | WORKING (50 ms) |

### `research-execution`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/research-execution/build` | not probed |
| GET | `/v1/research-execution/constitution` | WORKING (3 ms) |
| GET | `/v1/research-execution/dashboard` | WORKING (2948 ms) |
| POST | `/v1/research-execution/diagnostics` | not probed |
| POST | `/v1/research-execution/enrich` | not probed |
| POST | `/v1/research-execution/export` | not probed |
| GET | `/v1/research-execution/health` | WORKING (4 ms) |
| POST | `/v1/research-execution/plan` | not probed |
| GET | `/v1/research-execution/quality-gates` | WORKING (3008 ms) |

### `research-objective`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research-objective/constitution` | WORKING (5 ms) |
| GET | `/v1/research-objective/dashboard` | WORKING (164 ms) |
| POST | `/v1/research-objective/diagnostics` | not probed |
| GET | `/v1/research-objective/health` | WORKING (3 ms) |
| POST | `/v1/research-objective/plan` | not probed |
| GET | `/v1/research-objective/quality-gates` | WORKING (163 ms) |

### `research-office`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research-office/company/{ticker}` | not probed |
| GET | `/v1/research-office/dashboard` | WORKING (4 ms) |
| GET | `/v1/research-office/health` | WORKING (4 ms) |
| GET | `/v1/research-office/history` | WORKING (4 ms) |
| GET | `/v1/research-office/publications` | WORKING (4 ms) |
| GET | `/v1/research-office/queue` | WORKING (3 ms) |
| GET | `/v1/research-office/replay` | WORKING — needs query param |
| GET | `/v1/research-office/watchlists` | WORKING (4 ms) |

### `research-ontology`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/research-ontology/classify` | not probed |
| GET | `/v1/research-ontology/constitution` | WORKING (3 ms) |
| GET | `/v1/research-ontology/dashboard` | WORKING (4 ms) |
| GET | `/v1/research-ontology/health` | WORKING (3 ms) |
| GET | `/v1/research-ontology/quality-gates` | WORKING (4 ms) |

### `research-questions`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research-questions/constitution` | WORKING (3 ms) |
| GET | `/v1/research-questions/dashboard` | WORKING (3984 ms) |
| POST | `/v1/research-questions/diagnostics` | not probed |
| GET | `/v1/research-questions/health` | WORKING (4 ms) |
| POST | `/v1/research-questions/plan` | not probed |
| GET | `/v1/research-questions/quality-gates` | WORKING (3996 ms) |

### `research-writer`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/research-writer/health` | WORKING (6 ms) |
| GET | `/v1/research-writer/quality-gates` | WORKING (4 ms) |

### `rms`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/rms/approve` | not probed |
| GET | `/v1/rms/dashboard` | WORKING (2 ms) |
| POST | `/v1/rms/draft` | not probed |
| GET | `/v1/rms/health` | WORKING (2 ms) |
| POST | `/v1/rms/publish` | not probed |
| POST | `/v1/rms/request` | not probed |
| GET | `/v1/rms/research/{research_id}` | not probed |
| POST | `/v1/rms/review` | not probed |

### `root-cause-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/root-cause-intelligence/analyze` | WORKING (196 ms) |
| GET | `/v1/root-cause-intelligence/dashboard` | WORKING (4 ms) |
| GET | `/v1/root-cause-intelligence/health` | WORKING (3 ms) |
| GET | `/v1/root-cause-intelligence/history` | WORKING (6 ms) |
| GET | `/v1/root-cause-intelligence/nightly` | WORKING (7714 ms) |
| GET | `/v1/root-cause-intelligence/report` | WORKING (5 ms) |

### `rsp`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/rsp/committee` | not probed |
| GET | `/v1/rsp/evidence/{evidence_id}` | not probed |
| GET | `/v1/rsp/health` | WORKING (3 ms) |
| POST | `/v1/rsp/reason` | not probed |
| GET | `/v1/rsp/reasoning/{reasoning_id}` | not probed |
| POST | `/v1/rsp/synthesize` | not probed |

### `scheduler`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/scheduler/dashboard` | WORKING (5 ms) |
| GET | `/v1/scheduler/health` | WORKING (4 ms) |
| GET | `/v1/scheduler/history` | WORKING (4 ms) |
| GET | `/v1/scheduler/reports` | WORKING (4 ms) |
| POST | `/v1/scheduler/retry` | not probed |
| POST | `/v1/scheduler/run` | not probed |
| GET | `/v1/scheduler/status` | WORKING (3 ms) |
| GET | `/v1/scheduler/telemetry` | WORKING (3 ms) |
| GET | `/v1/scheduler/workflows` | WORKING (4 ms) |

### `sif`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/sif/analyse` | not probed |
| GET | `/v1/sif/dashboard` | WORKING (184 ms) |
| GET | `/v1/sif/frameworks` | WORKING (5 ms) |
| GET | `/v1/sif/frameworks/{sector_id}` | not probed |
| GET | `/v1/sif/health` | WORKING (3 ms) |
| GET | `/v1/sif/quality-gates` | WORKING (161 ms) |

### `simulation`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/simulation/dashboard` | WORKING (6 ms) |
| GET | `/v1/simulation/health` | WORKING (3 ms) |
| GET | `/v1/simulation/history` | WORKING (3 ms) |
| POST | `/v1/simulation/portfolio` | not probed |
| GET | `/v1/simulation/quality-gates` | WORKING (10 ms) |
| POST | `/v1/simulation/run` | not probed |
| GET | `/v1/simulation/scenarios` | WORKING (3 ms) |

### `temporal-integrity`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/temporal-integrity/certification` | WORKING (3 ms) |
| GET | `/v1/temporal-integrity/dashboard` | WORKING (3 ms) |
| GET | `/v1/temporal-integrity/health` | WORKING (3 ms) |
| GET | `/v1/temporal-integrity/rejected` | WORKING (5 ms) |
| GET | `/v1/temporal-integrity/replay` | WORKING (3 ms) |
| GET | `/v1/temporal-integrity/telemetry` | WORKING (3 ms) |
| POST | `/v1/temporal-integrity/validation` | not probed |

### `thesis-engine`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/thesis-engine/constitution` | WORKING (3 ms) |
| GET | `/v1/thesis-engine/dashboard` | WORKING (787 ms) |
| POST | `/v1/thesis-engine/diagnostics` | not probed |
| GET | `/v1/thesis-engine/health` | WORKING (4 ms) |
| POST | `/v1/thesis-engine/plan` | not probed |
| GET | `/v1/thesis-engine/quality-gates` | WORKING (875 ms) |

### `ui`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ui/article/{article_id}` | not probed |
| GET | `/v1/ui/autocomplete` | WORKING (43 ms) |
| GET | `/v1/ui/calendar` | WORKING (35 ms) |
| GET | `/v1/ui/company/{ticker}` | not probed |
| GET | `/v1/ui/copilot` | WORKING (8 ms) |
| GET | `/v1/ui/dashboard` | WORKING (35 ms) |
| GET | `/v1/ui/health` | WORKING (4 ms) |
| GET | `/v1/ui/home` | WORKING (40 ms) |
| GET | `/v1/ui/macro` | WORKING (10 ms) |
| GET | `/v1/ui/portfolio` | WORKING (3 ms) |
| GET | `/v1/ui/predictions` | WORKING (36 ms) |
| GET | `/v1/ui/research/{research_id}` | not probed |
| POST | `/v1/ui/search` | not probed |
| GET | `/v1/ui/sector/{sector_id}` | not probed |
| GET | `/v1/ui/theme/{theme_id}` | not probed |
| GET | `/v1/ui/timeline/{entity}` | not probed |
| GET | `/v1/ui/workflow` | WORKING (3 ms) |

### `universe-intelligence`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/universe-intelligence/company/{ticker}` | not probed |
| GET | `/v1/universe-intelligence/coverage-level/{ticker}` | not probed |
| GET | `/v1/universe-intelligence/dashboard` | WORKING (1367 ms) |
| GET | `/v1/universe-intelligence/health` | WORKING (6 ms) |
| GET | `/v1/universe-intelligence/ici/{ticker}` | not probed |
| GET | `/v1/universe-intelligence/membership` | WORKING — needs query param |
| GET | `/v1/universe-intelligence/memberships/{ticker}` | not probed |
| GET | `/v1/universe-intelligence/quality-gates` | WORKING (4250 ms) |
| POST | `/v1/universe-intelligence/run` | not probed |
| GET | `/v1/universe-intelligence/tree` | WORKING (8 ms) |
| GET | `/v1/universe-intelligence/universes` | WORKING (5 ms) |
| GET | `/v1/universe-intelligence/universes/{universe_id}` | not probed |

### `validation`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/validation/dashboard/{run_id}` | not probed |
| GET | `/v1/validation/datasets` | WORKING (3 ms) |
| GET | `/v1/validation/health` | WORKING (2 ms) |
| POST | `/v1/validation/replay` | not probed |
| GET | `/v1/validation/runs` | WORKING (2 ms) |
| GET | `/v1/validation/runs/{run_id}` | not probed |

### `validation-engine`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/validation-engine/constitution` | WORKING (3 ms) |
| GET | `/v1/validation-engine/dashboard` | WORKING (766 ms) |
| POST | `/v1/validation-engine/diagnostics` | not probed |
| POST | `/v1/validation-engine/enrich` | not probed |
| GET | `/v1/validation-engine/health` | WORKING (4 ms) |
| POST | `/v1/validation-engine/plan` | not probed |
| GET | `/v1/validation-engine/quality-gates` | WORKING (740 ms) |
| POST | `/v1/validation-engine/validate` | not probed |

### `ve`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/ve/company/{key}` | not probed |
| GET | `/v1/ve/compare` | WORKING — needs query param |
| GET | `/v1/ve/consult` | WORKING — needs query param |
| GET | `/v1/ve/dashboard` | WORKING (3 ms) |
| GET | `/v1/ve/health` | WORKING (2 ms) |
| GET | `/v1/ve/history` | WORKING — needs query param |
| GET | `/v1/ve/model` | WORKING — needs query param |
| GET | `/v1/ve/scenarios` | WORKING — needs query param |
| GET | `/v1/ve/search` | WORKING — needs query param |
| GET | `/v1/ve/sensitivity` | WORKING — needs query param |
| GET | `/v1/ve/valuation/{valuation_id}` | not probed |
| POST | `/v1/ve/value` | not probed |

### `yfp`

| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/yfp/dashboard` | WORKING (4 ms) |
| POST | `/v1/yfp/enrich/{ticker}` | not probed |
| GET | `/v1/yfp/health` | WORKING (3 ms) |
| GET | `/v1/yfp/quality-gates` | WORKING (4 ms) |
| GET | `/v1/yfp/search` | WORKING — needs query param |

## Notes

- `not probed` = `POST`/`PUT`/`DELETE` or a path-parameter route (needs an id). Spot checks passed: `/v1/institutional-evaluation-lab/question/CIO-Q01`, `/v1/institutional-analog-intelligence/memory/{id}`.
- Common required query param is `q` (search/consult endpoints). Others: `as_of`, `pipeline_id`, `replay_id`, `name`, `source`/`target`, `companies`, `ticker`.
- Token-protected: `/v1/features*`, `/v1/research/runs`, `/v1/eval/predictions/pending`, `/v1/orch/l2/builds`. Verified 200 with `Authorization: Bearer`.
- Slowest healthy endpoints: `mission-control/dashboard` (~13 s), `live-data/verification/probes` (~10 s), IEL/RCI `nightly` (~8 s).
