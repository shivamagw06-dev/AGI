# FSE-02.1 — Canonical Ingestion Migration

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — implementation in progress |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-02.1 |
| **Depends on** | [FSE-02](FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md) · [FSE-00](FSE_00_PIPELINE_ORCHESTRATOR.md) · FSE-01 Raw Evidence Layer |
| **Package** | `intelligence-engine/financial_statements_engine/collection/` |
| **Canonical API** | `collection.ingest.ingest(...)` |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · parsers · validation · warehouse · DME consumers |

### Document series

| ID | Document | Role |
| --- | --- | --- |
| FSE-02 | Data Sources & Collection Pipeline | Collectors & Raw Evidence Writer |
| **FSE-02.1** | **Canonical Ingestion Migration** | **Single path: collectors → FSE-02 → raw store → `evidence.stored`** |
| FSE-00 | Pipeline Orchestrator | Subscribes to `evidence.stored` and runs PARSE → VALIDATE → WAREHOUSE → DME |

---

# 1. Mission

Transform FSE-02 from an unused collector into the **single canonical ingestion layer** for every financial statement entering AGIB.

```text
NSE
BSE
Company IR
Yahoo (fallback only)
        │
        ▼
Collectors (adapters)
        │
        ▼
FSE-02 ingest()
        │
        ▼
Raw Evidence Store
        │
        ▼
evidence.stored
        │
        ▼
Pipeline Orchestrator
        │
        ▼
PARSE → VALIDATE → WAREHOUSE → DME
```

There must be **one canonical path**.

---

# 2. Scope

## In scope

* Collector adapters that call `FSE-02 ingest()` instead of treating HD as the system of record for first entry
* Raw Evidence Store growth (bytes + metadata; no parse)
* Exactly one `evidence.stored` emission per successful new ingest
* Temporary dual-write to Historical Depth (HD)
* Idempotency (document hash / logical key)
* Mission Control ingestion dashboard
* Migration tests for the end-to-end ingestion trigger

## Out of scope (this phase)

* Removing HD
* Disabling HD writers
* Migrating consumers off HD
* Changing parser, validation, warehouse, or DME logic
* Making Financial Warehouse the sole authoritative consumer source (later phase)

---

# 3. Phases

## Phase 1 — Collector adapter

Collectors become adapters. Storage decisions move into FSE-02:

```text
Collector → FSE-02 ingest()
```

## Phase 2 — Raw Evidence Store

Every successful collection stores raw bytes, metadata, source, timestamps, document hash, company, filing type, and period. Nothing is parsed here.

## Phase 3 — Event emission

Every successful **new** ingest emits exactly one `evidence.stored`. Collectors never call Parse. The orchestrator handles everything else.

## Phase 4 — Temporary dual-write

```text
Collector
   ↓
FSE-02
   ├── Raw Evidence (+ evidence.stored)
   └── Existing HD write (unchanged shape)
```

Consumers continue working against HD.

## Phase 5 — Idempotency

If the same filing is collected twice:

* verify document hash
* do not duplicate raw evidence
* do not emit a second `evidence.stored` (and thus no duplicate workflow)
* log duplicate detection (`evidence.duplicate_skipped`)

## Phase 6 — Mission Control

Ingestion dashboard tracks: collected today, duplicate filings, failed downloads, stored evidence, event emissions, average ingest latency, source distribution, latest filing time.

## Phase 7 — Success criteria

For one company, without manual CLI intervention:

```text
Collect → Raw Evidence Stored → evidence.stored → Workflow Created
  → Parse → Validate → Warehouse → DME
```

---

# 4. Feature flags

| Env | Default | Meaning |
| --- | --- | --- |
| `FSE_02_CANONICAL_INGEST` | `true` | Route adapter collectors through `ingest()` |
| `FSE_02_DUAL_WRITE_HD` | `true` | Keep writing HD after successful FSE-02 path |

**Rule:** Do not disable HD writers in this phase. Dual-write stays on until the Financial Warehouse is authoritative for all downstream consumers.

---

# 5. Canonical API

```python
from financial_statements_engine.collection.ingest import ingest

result = ingest(
    ticker="TCS",
    content=raw_bytes,
    source="nse_xbrl",
    document_type="xbrl",
    period_type="annual",
    period_end="2025-03-31",
    source_url="https://...",
    collector="earnings_intelligence",
)
```

`ingest()` is responsible for:

1. Idempotent raw write (`write_evidence`)
2. Emitting `evidence.stored` **only** on new storage / restatement candidates
3. Recording Mission Control metrics
4. Optionally invoking an HD dual-write callback when `FSE_02_DUAL_WRITE_HD` is enabled

`evidence.stored` payload **must** include `ticker`, `evidence_id`, `content_sha256`, `period_end` / `period`, `period_type` / `document_type`, and `source` so the orchestrator can form a stable workflow identity.

---

# 6. Adapter mapping

| Collector | Adapter behaviour |
| --- | --- |
| FSE-02 collection jobs (`run_job`) | Call `ingest()` after integrity verify |
| Earnings Intelligence XBRL download | After bytes available → `ingest()`; keep pack parse + HD `persist_pack` |
| FinancialStatementsConnector | Serialize records as structured JSON evidence → `ingest()`; keep HD `put_series` |
| Yahoo / failover structured pulls | Same structured-JSON ingest when bytes/records exist; HD dual-write remains |

---

# 7. Acceptance criteria

* Every financial-statement collector submits evidence through FSE-02
* FSE Raw Evidence Store begins growing
* One filing automatically creates one workflow (via `evidence.stored` + FSE-00)
* Duplicate ingestion is prevented
* HD still functions via temporary dual-write
* No existing consumer breaks
* Existing tests continue to pass
* New migration tests validate the end-to-end ingestion trigger

---

# 8. Surfaces

| Surface | Path |
| --- | --- |
| CLI | `python -m financial_statements_engine --ingest-dashboard` |
| HTTP | `GET /v1/financial-statements/collection/ingest-dashboard` |
| Spec pointer | `intelligence-engine/docs/FSE_02_1.md` |
