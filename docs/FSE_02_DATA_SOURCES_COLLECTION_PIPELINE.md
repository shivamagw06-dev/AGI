# FSE-02 — Data Sources & Collection Pipeline

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-02 |
| **Depends on** | [FSE-01](FSE_01_FINANCIAL_STATEMENTS_ENGINE.md) (architecture & Raw Evidence Layer) |
| **Package** | `intelligence-engine/financial_statements_engine/collection/` |
| **Engine surface** | `financial_statements_engine` (collection subsystem) |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine formulas · Institutional Gate · Evaluation Lab · IAT · Mission Control contracts |

### Document series

| ID | Document | Role |
| --- | --- | --- |
| FSE-01 | Architecture & Principles | What the architecture is |
| **FSE-02** | **Data Sources & Collection Pipeline** | **How data enters the architecture** |
| FSE-02.1 | [Canonical Ingestion Migration](FSE_02_1_CANONICAL_INGESTION_MIGRATION.md) | Collectors → FSE-02 ingest() → raw store → `evidence.stored` (HD dual-write) |
| FSE-02.2 | [End-to-End Production Verification](FSE_02_2_END_TO_END_PRODUCTION_VERIFICATION.md) | Timed pipeline proof · reports · provenance · SLA · DLQ recovery |
| FSE-02.3 | [Official Source Registry](FSE_02_3_OFFICIAL_SOURCE_REGISTRY.md) | MCA → NSE → BSE → IR adapters · registry · fallback |
| FSE-03 | [Canonical Financial Data Model & Schema](FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md) | Authoritative financial representation |
| FSE-04 | [Parsing & Normalization Engine](FSE_04_PARSING_NORMALIZATION_ENGINE.md) | Raw evidence → canonical statement drafts |
| FSE-04.1 | [Parse Manifest, Replay & Certification](FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md) | Parser audit / replay / certification |
| FSE-04.2 | [Evidence Coverage Matrix & Extraction Audit](FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md) | Extraction coverage audit (before validation) |
| FSE-04.3 | [Production Certification Corpus & Golden Dataset](FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md) | Permanent parser certification ground truth |
| FSE-05 | [Validation & Financial Quality Engine](FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) | Canonical drafts → validated warehouse facts |
| FSE-06 | [Financial Warehouse](FSE_06_FINANCIAL_WAREHOUSE.md) | Immutable validated facts · versions · contracts |
| FSE-07 | Derived Metrics Engine | Financial intelligence from validated facts |
| FSE-08 | Forecast & Estimates Engine | Forward estimates on DME metrics |
| FSE-09 | Financial Time-Series & Revision Engine | Revisions · restatement timelines |
| FSE-10 | Financial Intelligence APIs | Governed consumer surfaces |

---

# 1. Purpose

The Data Sources & Collection Pipeline is responsible for acquiring every financial statement required by the Financial Statements Engine (FSE).

Its purpose is to ensure that AGIB continuously receives complete, timely, and verifiable financial data from authoritative sources.

Collectors do **not** interpret, calculate, or modify financial information. They only discover, retrieve, verify, and deliver source evidence to the Raw Evidence Layer.

---

# 2. Objectives

The collection pipeline shall:

* Discover new financial filings automatically.
* Retrieve documents from trusted sources.
* Preserve all original evidence.
* Detect updates and restatements.
* Avoid duplicate downloads.
* Operate continuously.
* Support historical backfill and live collection.
* Guarantee traceability from every downloaded document to its source.
* Emit evidence events without blocking on downstream parsers.

---

# 3. Collection Principles

## 3.1 Official Sources First

Priority order:

1. NSE
2. BSE
3. Company Investor Relations
4. XBRL repositories
5. Annual Reports
6. Quarterly Results
7. MCA (validation only)

Unofficial or third-party sources may supplement discovery but must not replace official filings for canonical financial data.

## 3.2 Source Hierarchy

If the same reporting period exists in multiple places:

1. Official XBRL
2. Official exchange filing
3. Company IR
4. Annual report PDF

Lower-priority sources may not overwrite higher-priority evidence.

Implementation constant: `SOURCE_PRIORITY` in `collection/sources.py` (lower integer = higher priority).

## 3.3 Immutable Evidence

Every downloaded file is stored exactly as received.

No collector may modify:

* PDFs
* HTML
* XBRL
* Excel
* ZIP archives

## 3.4 Idempotent Collection

Running the same collector twice must never create duplicate evidence.

Evidence uniqueness is based on:

* `content_sha256` (primary)
* plus logical identity: `source`, `ticker`/`entity`, `reporting period`, `filing_date`, `document_type`

Identical content hash ⇒ skip store; emit `evidence.duplicate_skipped` event.

## 3.5 Collectors Never Parse

Collectors stop at Raw Evidence + event emission.

Parsing belongs to FSE-04 (and the Extraction Layer from FSE-01). Collection must not call normalizers, validators, or warehouse publish paths.

---

# 4. Architectural Improvement — Evidence Event Bus

FSE-02 introduces an **Evidence Event Bus** between collection and processing.

### Forbidden coupling

```text
Collector → Parser   ❌
```

### Required topology

```text
Collector
    ↓
Raw Evidence Layer (immutable store)
    ↓
Evidence Event Bus
    ↓
  ┌─────────────┬──────────────┬──────────────┐
  ▼             ▼              ▼              ▼
Parser     Normalizer     Validator     Observability
(FSE-04)   (FSE-04)       (FSE-05)      (FSE-08)
```

### Why

* Collectors continue ingesting when parsers are busy or unavailable
* Horizontal scaling of collectors and processors independently
* Multiple subscribers can react to the same evidence (parse, DQ, Mission Control)
* Restatement / reprocess triggers are explicit events, not hidden side effects

### Event bus requirements (v1)

| Requirement | Spec |
| --- | --- |
| Transport | Local durable JSONL + in-process subscribers (v1); pluggable backend interface for Redis/SQS later |
| Delivery | At-least-once |
| Ordering | Per `(ticker, period_end, document_type)` best-effort FIFO |
| Idempotency | Consumers key on `event_id` / `evidence_id` |
| Failure | Failed consumer handlers do not fail the collector write |
| Retention | Event log retained for audit (configurable days; default 90) |

Module: `financial_statements_engine/collection/event_bus.py`

---

# 5. Supported Sources

## 5.1 NSE

Collect:

* Annual Results
* Quarterly Results
* XBRL
* Corporate Filings
* Financial Statements

Primary adapter (existing): `earnings_intelligence.discovery` / Integrated Filing index — wrapped by `collection/adapters/nse.py`.

## 5.2 BSE

Collect:

* Annual Reports
* Quarterly Results
* Exchange Filings
* Financial Statements

Adapter: `collection/adapters/bse.py` (may soft-delegate to existing BSE connectors; must not invent financial figures).

## 5.3 Company IR

Collect:

* Annual Reports
* Investor Presentations
* Earnings Releases
* Financial Supplements
* Historical Reports

Adapter: `collection/adapters/ir.py` (discovery-assisted; lower priority than exchange XBRL).

## 5.4 XBRL

Collect:

* Tagged financial statements
* Reporting metadata
* Filing metadata
* Taxonomy version

## 5.5 Annual Reports

Evidence types for later extraction (FSE-04):

* Financial statements
* Notes
* Segment reporting
* Auditor information
* Share capital details

## 5.6 Quarterly Results

Collect:

* Standalone statements
* Consolidated statements
* Quarterly notes
* Financial highlights

### Source codes (canonical)

```text
nse_integrated_filing
nse_corporates_financial_results
nse_xbrl
bse_filing
bse_xbrl
company_ir
xbrl_repository
annual_report_pdf
quarterly_results
mca_validation
```

---

# 6. Collector Types

The pipeline consists of specialised collectors. Responsibilities must not overlap (FSE-01 Principle 6 / Separation of Concerns).

## 6.1 Discovery Collector

Detects:

* New filings
* Updated filings
* Restatements (candidate)

Outputs **discovery events only** (`discovery.filing_found`, `discovery.filing_updated`).

Never downloads binary content.

Module: `collection/discovery.py`

## 6.2 Downloader

Downloads documents.

Never parses.

Module: `collection/downloader.py`

## 6.3 Metadata Collector

Extracts:

* Filing dates
* Reporting period
* Exchange reference
* Company identifier
* Document identifiers
* Taxonomy version (when present in headers / index rows)

Does not interpret accounting line items.

Module: `collection/metadata.py`

## 6.4 Integrity Verifier

Verifies:

* File size
* Hash (SHA-256)
* Checksum (when provided by source)
* Download completeness (non-empty; content-type sanity)

Module: `collection/integrity.py`

## 6.5 Raw Evidence Writer

Stores:

* Original file
* Metadata
* Retrieval timestamp
* Source information

Uses FSE-01 `raw_evidence.store_raw` — never a parallel immutable store.

Module: `collection/writer.py` (thin façade over `raw_evidence.py`)

---

# 7. Collection Lifecycle

Every document follows this lifecycle:

```text
Discover
  → Queue
  → Download
  → Verify
  → Generate Hash
  → Store Raw
  → Emit Processing Event
```

No collector proceeds beyond raw storage + event emission.

### State machine (job)

```text
queued
  → discovering
  → discovered
  → downloading
  → downloaded
  → verifying
  → verified
  → stored
  → event_emitted
  → completed

  ↘ failed_transient → (retry with backoff) → queued
  ↘ failed_permanent → dead_letter
  ↘ skipped_duplicate → completed
```

---

# 8. Job Model

Every collection task represents a single unit of work.

A job consists of:

| Field | Required | Description |
| --- | --- | --- |
| `job_id` | yes | Stable UUID / deterministic hash |
| `ticker` | yes | Exchange ticker (NSE symbol) |
| `entity` | no | Resolved entity (e.g. TMPV) |
| `source` | yes | Source code from §5 |
| `document_type` | yes | `xbrl`, `pdf`, `html`, `xlsx`, `zip` |
| `period_type` | yes | `annual` / `quarterly` / `unknown` |
| `period_end` | no | ISO date when known |
| `mode` | yes | `live` / `historical` |
| `priority` | yes | Integer; lower = sooner |
| `attempt` | yes | Retry count |
| `discovery_ref` | no | Upstream discovery event id |

Jobs are independent and retryable.

Module: `collection/jobs.py`

---

# 9. Scheduling

Two scheduling modes exist.

## 9.1 Live Collection

Runs continuously.

Triggers:

* New filings
* Exchange updates
* IR updates

Goal: acquire new evidence quickly.

CLI/API: `collect --mode live`

## 9.2 Historical Collection

Runs until complete.

Priority:

1. Latest Annual
2. Latest Quarter
3. Five-year history
4. Ten-year history
5. Archive

**Coverage is prioritised over historical depth** (FSE-01 Principle 7).

Deep archive / historical depth work uses this same job model (roadmap after DME).

Module: `collection/scheduler.py`

---

# 10. Retry Policy

Collectors retry only transient failures.

Examples:

* Timeout
* Connection interruption
* Temporary server error (HTTP 429 / 503)

Permanent failures (404 not found for known-bad URL, unsupported media after verify, auth denied) are recorded and escalated to dead-letter + observability.

### Policy (v1)

| Parameter | Value |
| --- | --- |
| Max attempts | 5 |
| Backoff | Exponential: `min(2^attempt, 60)` seconds (+ jitter 0–250ms) |
| Retryable HTTP | 408, 429, 500, 502, 503, 504 |
| Non-retryable HTTP | 400, 401, 403, 404, 410 |

Module: `collection/retry.py`

---

# 11. Duplicate Detection

Before storing new evidence:

1. Compute content hash (SHA-256).
2. Compare with existing evidence for that hash.
3. Skip identical documents (`skipped_duplicate`).
4. Create a new evidence version only if the content differs.

Logical restatement path (§12) applies when period identity matches but hash differs.

---

# 12. Restatement Detection (collection side)

When a document for an existing reporting period changes:

1. Detect the difference (hash ≠ prior evidence for same logical key).
2. Store as **new** evidence (immutable; never overwrite).
3. Publish a restatement event on the Evidence Event Bus: `evidence.restatement_candidate`.
4. Downstream (FSE-06) performs statement-level versioning / warehouse restatement.

Collection does not rewrite published warehouse statements.

Logical key:

```text
(ticker, period_type, period_end, document_type, consolidation)
```

---

# 13. Evidence Event Bus — Event Catalogue

| Event type | When | Payload (min) |
| --- | --- | --- |
| `discovery.filing_found` | Discovery sees new filing | ticker, source, url, period_*, document_type |
| `discovery.filing_updated` | Index row changed | prior_ref, new_ref |
| `evidence.stored` | Raw evidence written | evidence_id, ticker, source, content_sha256, path |
| `evidence.duplicate_skipped` | Hash already present | evidence_id, ticker |
| `evidence.restatement_candidate` | Same period, new hash | evidence_id, prior_evidence_id, logical_key |
| `collection.job_failed` | Permanent failure | job_id, error_code, detail |
| `collection.job_completed` | Terminal success/skip | job_id, status |

Consumers (subscribers) in later FSE docs:

* FSE-04 parser/normalizer
* FSE-05 validator (optional early structural)
* FSE-06 versioning
* FSE-08 Mission Control metrics

---

# 14. Collection Metrics

Every collector reports:

* Runtime
* Throughput
* Success rate
* Failure rate
* Retry count
* Queue depth
* Download latency
* Freshness
* Coverage
* Duplicate rate
* Event bus lag (events produced − consumed, per subscriber)

These metrics feed Mission Control (FSE-08). v1 exposes:

* `GET /v1/financial-statements/collection/health`
* `GET /v1/financial-statements/collection/dashboard`
* JSONL under `$FSE_STORE_ROOT/observability/collection_metrics.jsonl`

---

# 15. Security & Compliance

Collectors must:

* Respect robots.txt and applicable terms where appropriate.
* Identify themselves with a configurable user agent (`FSE_HTTP_USER_AGENT`).
* Avoid abusive request rates (`FSE_HTTP_MIN_INTERVAL_MS`, default 200ms per host).
* Log all retrieval activity.
* Preserve evidence for audit purposes.
* Never embed secrets in evidence metadata.

---

# 16. Quality / Success Criteria

The Collection Pipeline is considered production-ready when it achieves:

| Metric | Target |
| --- | --- |
| Successful downloads | >99% |
| Duplicate storage | <0.1% |
| Evidence traceability | 100% |
| Restatement detection | 100% |
| Raw evidence preservation | 100% |
| Retry recovery | >95% |
| Collector uptime | >99% |
| Event emission after store | 100% |

---

# 17. Module Mapping (implement exactly)

```text
financial_statements_engine/collection/
  __init__.py
  schema.py          # job statuses, event types, targets
  sources.py         # official priority + hierarchy
  discovery.py       # discovery collector
  downloader.py      # bytes only
  metadata.py        # filing metadata (no line items)
  integrity.py       # size/hash/completeness
  writer.py          # raw evidence writer façade
  jobs.py            # job model + queue
  retry.py           # backoff policy
  scheduler.py       # live vs historical ordering
  event_bus.py       # Evidence Event Bus
  pipeline.py        # Discover→…→Emit orchestration
  adapters/
    nse.py           # wraps earnings_intelligence discovery
    bse.py
    ir.py
  production.py      # health/dashboard/run façades
```

Storage additions under `$FSE_STORE_ROOT`:

```text
collection/
  jobs/<job_id>.json
  queue.jsonl
  dead_letter.jsonl
  discovery/<ticker>/<discovery_id>.json
events/
  bus.jsonl                 # durable event log
  cursors/<subscriber>.json # consumer offsets
```

---

# 18. Public Interfaces

## CLI

```bash
export PYTHONPATH=.
python -m financial_statements_engine --collection-health
python -m financial_statements_engine --collection-dashboard
python -m financial_statements_engine --collect TCS
python -m financial_statements_engine --collect TCS --mode historical
python -m financial_statements_engine --collect-universe gold --mode live
```

## HTTP

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/financial-statements/collection/health` | Collector subsystem health |
| GET | `/v1/financial-statements/collection/dashboard` | Queue/coverage/metrics |
| POST | `/v1/financial-statements/collection/run` | Enqueue/run jobs for ticker |
| GET | `/v1/financial-statements/collection/events` | Tail recent bus events |

## Python

```python
from financial_statements_engine.collection.production import (
    health,
    dashboard,
    collect_ticker,
    run_universe,
)
from financial_statements_engine.collection.event_bus import subscribe, publish, EventBus
```

Payloads must include `issues_recommendations: false` and must not emit BUY/SELL.

---

# 19. Integration with FSE-01 layers

| FSE-01 layer | FSE-02 interaction |
| --- | --- |
| Official Sources | Source registry + adapters |
| Raw Evidence Layer | Sole write target for collectors |
| Extraction Layer | **Subscriber** to `evidence.stored` (not called inline) |
| Normalization+ | Not invoked by collectors |
| Warehouse | Not written by collectors |

Migration note: existing `ingest_and_publish` convenience path in FSE-01 M1 may still call extraction inline for bootstrapping. New collection code paths **must** use the Event Bus. Inline ingest is deprecated after FSE-04 lands.

---

# 20. Test Requirements

Minimum tests:

1. Source hierarchy: XBRL priority beats IR for same period
2. Idempotent store: identical bytes ⇒ one evidence object + `duplicate_skipped` event
3. Restatement candidate: same logical key, different hash ⇒ second evidence + restatement event
4. Retry policy classifies 503 as transient and 404 as permanent
5. Pipeline stops at raw store (mock parser never called)
6. Event bus delivers `evidence.stored` to a test subscriber
7. Collector health reports workstream `FSE-02`
8. No recommendation / BUY / SELL fields in public payloads

---

# 21. Non-Goals (v1)

* Parsing XBRL/PDF into line items (FSE-04)
* Accounting validation (FSE-05)
* Warehouse publish (FSE-01 warehouse / FSE-06)
* BUY/SELL or research recommendations
* Abusive high-concurrency scraping
* Replacing Mission Control contracts

---

# 22. Implementation Checklist (coding agents)

Implement in order:

- [ ] `collection/schema.py` + `sources.py`
- [ ] `collection/event_bus.py` (publish/subscribe + JSONL durability)
- [ ] `collection/jobs.py` + `retry.py` + `scheduler.py`
- [ ] `collection/integrity.py` + `writer.py`
- [ ] `collection/metadata.py` + `discovery.py` + `downloader.py`
- [ ] `collection/adapters/nse.py` (wrap P2.1 discovery)
- [ ] `collection/pipeline.py` (full lifecycle)
- [ ] `collection/production.py` + CLI flags + HTTP routes
- [ ] Tests in §20
- [ ] Cross-link from FSE-01 series index

**Acceptance for this PR:** FSE-02 spec committed; collection package importable; event bus + idempotent raw write + hierarchy + retry tests green; collectors do not call parsers.
