# FSE-01 — Financial Statements Engine

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-01 |
| **Package** | `intelligence-engine/financial_statements_engine/` |
| **Engine code** | `financial_statements_engine` |
| **Predecessor** | P2.1 `earnings_intelligence` (becomes Extraction adapter, not a parallel warehouse) |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine formulas · Institutional Gate · Evaluation Lab · IAT · Mission Control contracts |

### Document series

| ID | Document | Role |
| --- | --- | --- |
| **FSE-01** | **Architecture & Principles** | **What the architecture is** |
| FSE-02 | [Data Sources & Collection Pipeline](FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md) | How data enters the architecture |
| FSE-03 | [Canonical Financial Data Model & Schema](FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md) | Authoritative financial representation |
| FSE-04 | [Parsing & Normalization Engine](FSE_04_PARSING_NORMALIZATION_ENGINE.md) | Raw evidence → canonical statement drafts |
| FSE-04.1 | [Parse Manifest, Replay & Certification](FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md) | Parser audit / replay / certification |
| FSE-04.2 | [Evidence Coverage Matrix & Extraction Audit](FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md) | Extraction coverage audit (before validation) |
| FSE-04.3 | [Production Certification Corpus & Golden Dataset](FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md) | Permanent parser certification ground truth |
| FSE-05 | [Validation & Financial Quality Engine](FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) | Canonical drafts → validated warehouse facts |
| FSE-06 | [Financial Warehouse](FSE_06_FINANCIAL_WAREHOUSE.md) | Immutable validated facts · versions · contracts |
| FSE-00 | Pipeline Orchestrator | Coordinates RAW→PARSE→VALIDATE→WAREHOUSE→DME |
| FSE-07 | Derived Metrics Engine | Financial intelligence from validated facts |
| FSE-ECD | Evidence Coverage Dashboard | How many companies at each pipeline stage |
| FSE-08 | Forecast & Estimates Engine | Forward estimates on DME metrics |
| FSE-09 | Financial Time-Series & Revision Engine | Revisions · restatement timelines |
| FSE-10 | Financial Intelligence APIs | Governed consumer surfaces |

---

# 1. Purpose

The Financial Statements Engine (FSE) is AGIB's canonical financial intelligence platform.

Its responsibility is to acquire, validate, normalize, version, and publish structured financial statements for every company in AGIB's investment universe.

The FSE is the **single source of truth** for financial information.

**No downstream component may bypass the FSE.**

---

# 2. Mission

Build an institutional-grade financial warehouse that matches the engineering principles of Bloomberg, Capital IQ, FactSet and Morningstar.

The objective is not to scrape reports.

The objective is to build a permanent financial knowledge system.

Every published financial figure must be:

* Correct
* Explainable
* Traceable
* Versioned
* Reproducible
* Auditable

---

# 3. Architectural Philosophy

The Financial Statements Engine is a **data platform**.

It is **not**:

* a web scraper
* an ETL script
* a parser
* a database table
* an AI summarizer

It is an institutional data platform responsible for the complete financial history of every company.

---

# 4. Design Principles

## Principle 1 — Financial correctness is absolute

No optimisation may reduce accounting accuracy.

## Principle 2 — Every number has evidence

Every stored financial figure must trace back to an official source.

There must never exist a financial value whose origin cannot be identified.

## Principle 3 — Raw data is immutable

Original filings are never modified.

Processing occurs in downstream layers only.

## Principle 4 — Canonical data is unique

Every financial concept exists once.

Example: Revenue must always become `revenue`.

There shall never be multiple internal names representing the same financial concept.

## Principle 5 — History is permanent

Historical statements are never overwritten.

New filings create new versions.

Previous versions remain permanently available.

## Principle 6 — Validation precedes publication

Financial statements are never published until validation completes.

Validation failures do not delete data.

Instead they change publication status.

## Principle 7 — Coverage before depth

Complete coverage of the investment universe is prioritised before expanding historical depth.

Example: 500 companies with 5 years of validated statements is preferable to 50 companies with 30 years of history.

## Principle 8 — One financial warehouse

Every downstream system reads from one canonical financial warehouse.

No system independently downloads or parses financial statements.

---

# 5. Architecture

The architecture is strictly layered.

```text
Official Sources
      ↓
Raw Evidence Layer
      ↓
Extraction Layer
      ↓
Normalization Layer
      ↓
Canonical Statement Layer
      ↓
Validation Layer
      ↓
Version Control Layer
      ↓
Financial Warehouse
      ↓
Derived Metrics Engine
      ↓
Consumers
```

No layer may bypass another.

### Package mapping (implement exactly)

| Layer | Module |
| --- | --- |
| Orchestration / CLI / health | `financial_statements_engine/production.py` |
| Contracts / versions / statuses | `financial_statements_engine/schema.py` |
| Canonical metric registry | `financial_statements_engine/registry.py` |
| Raw Evidence | `financial_statements_engine/raw_evidence.py` |
| Extraction (adapters) | `financial_statements_engine/extraction/` |
| NSE XBRL adapter (wraps P2.1) | `financial_statements_engine/extraction/nse_xbrl.py` |
| Normalization | `financial_statements_engine/normalize.py` |
| Canonical statements | `financial_statements_engine/canonical.py` |
| Validation | `financial_statements_engine/validate.py` |
| Version control | `financial_statements_engine/versioning.py` |
| Warehouse | `financial_statements_engine/warehouse.py` |
| Derived metrics | `financial_statements_engine/derived.py` |
| Observability | `financial_statements_engine/observability.py` |
| Persistence helpers | `financial_statements_engine/store.py` |

Persistence targets:

* Raw evidence blobs + checksums under FSE store root (see §18)
* Canonical published series continue to align with HD keys `financials_annual` / `financials_quarterly` so Company Memory / CID do not fork a second warehouse
* FSE adds publication metadata, validation status, and version lineage on top of those series

---

# 6. Data Flow

Every financial document follows the same lifecycle.

```text
Discover → Download → Verify → Store Raw → Evidence Event Bus
  → Extract → Normalize → Validate → Version → Publish → Index → Consume
```

Collection (FSE-02) stops at **Store Raw + Event Bus**. Downstream processors subscribe to evidence events and must not be invoked inline by collectors.

Every stage is independently testable and retryable.

### Lifecycle state machine

```text
discovered
  → downloaded
  → raw_verified
  → extracted
  → normalized
  → validation_pending
  → validated | validation_failed
  → versioned
  → published | withheld
  → indexed
```

Rules:

* `validation_failed` never deletes raw or extracted artifacts
* `withheld` is a publication status, not data deletion
* Consumers may read only `published` statements (plus explicit flagged modes for research diagnostics)
* Re-running the same filing identity is **idempotent**

---

# 7. Layer Responsibilities

## 7.1 Raw Evidence Layer

Responsible for:

* Original PDFs
* XBRL
* HTML filings
* Filing metadata
* Checksums (SHA-256)
* Retrieval timestamps
* Source URL / exchange identifier

**Never modified after write.**

### Evidence object (required fields)

```json
{
  "evidence_id": "sha256:<hex>",
  "ticker": "TCS",
  "entity": "TCS",
  "source": "nse_integrated_filing",
  "source_url": "https://...",
  "document_type": "xbrl",
  "period_type": "quarterly",
  "period_end": "2025-03-31",
  "fiscal_year": 2025,
  "fiscal_period": "Q4",
  "retrieved_at": "2026-07-29T00:00:00+00:00",
  "content_sha256": "<hex>",
  "bytes_path": "raw/<ticker>/<evidence_id>.xbrl",
  "immutable": true
}
```

## 7.2 Extraction Layer

Responsible for:

* Reading raw documents
* Parsing structured values
* Capturing unknown fields
* Parser confidence

**No business logic. No ratios. No synonym canonicalization beyond parser-local keys.**

### Extraction result

```json
{
  "evidence_id": "sha256:<hex>",
  "extractor": "nse_indas_xbrl_v1",
  "confidence": 0.0,
  "fields": {
    "RevenueFromOperations": {"value": 123.0, "unit": "INR_Crores", "raw_tag": "..."}
  },
  "unknown_fields": [],
  "errors": []
}
```

### Adapter rule

Primary India equity adapter is NSE IND-AS XBRL via existing `earnings_intelligence` parser logic, **imported behind** `extraction/nse_xbrl.py`.

Do **not** duplicate XBRL tag maps in consumers. Tag maps live in extraction only.

## 7.3 Normalization Layer

Responsible for:

* Standard terminology (registry)
* Units → base currency units (INR)
* Currency
* Period normalization
* Fiscal calendars
* Synonym mapping

**No calculations** (no ROE, no margins).

### Normalization rules (v1)

| Rule | Spec |
| --- | --- |
| Metric names | Must resolve through `registry.py` synonym → canonical |
| Currency | Store `currency=INR` and `unit_scale` (`ones`, `thousands`, `lakhs`, `crores`, `millions`) |
| Canonical numeric storage | Convert to `value_inr` in absolute INR (ones) where scale known; retain original `reported_value` + `unit_scale` |
| Period | `period_type` ∈ {`annual`,`quarterly`}; `period_end` ISO date; `fiscal_year`; `fiscal_period` (`FY`,`Q1`…`Q4`) |
| Missing mapping | Leave field in `unmapped`; never invent a canonical name |

## 7.4 Canonical Statement Layer

Produces standardized financial statements:

* Income Statement
* Balance Sheet
* Cash Flow
* Quarterly Results
* Annual Results

Every reporting period document is immutable once published.

### Canonical statement document

```json
{
  "statement_id": "TCS:quarterly:2025-03-31:income_statement:v3",
  "ticker": "TCS",
  "entity": "TCS",
  "statement_type": "income_statement",
  "period_type": "quarterly",
  "period_end": "2025-03-31",
  "fiscal_year": 2025,
  "fiscal_period": "Q4",
  "currency": "INR",
  "metrics": {
    "revenue": {
      "value_inr": 640540000000.0,
      "reported_value": 64054.0,
      "unit_scale": "crores",
      "evidence_id": "sha256:...",
      "extractor": "nse_indas_xbrl_v1",
      "confidence": 0.95
    }
  },
  "version": 3,
  "publication_status": "published",
  "validation_status": "passed",
  "as_of": "2026-07-29T00:00:00+00:00"
}
```

`statement_type` ∈:

* `income_statement`
* `balance_sheet`
* `cash_flow`
* `results_pack` (bundled IS/BS/CF for a period)

## 7.5 Validation Layer

Performs:

* Accounting validation
* Cross-source validation
* Structural validation
* Currency validation
* Completeness validation
* Consistency validation
* Outlier detection

**Validation never edits data.** It only emits status + issue codes.

### Required validation checks (v1)

| Code | Check |
| --- | --- |
| `STRUCT_REQUIRED_KEYS` | Required keys present for statement type |
| `ACCT_IS_IDENTITY` | Where present: `pat ≈ pbt - tax` within tolerance |
| `ACCT_BS_BALANCE` | Where present: assets ≈ liabilities + equity within tolerance |
| `ACCT_CF_BRIDGE` | Where present: OCF+ICF+FCF ≈ net change in cash within tolerance |
| `UNIT_CURRENCY` | Currency/scale coherent |
| `COMPLETENESS_CORE` | Core metrics present for publication tier |
| `OUTLIER_YOY` | YoY move beyond threshold flagged (not auto-corrected) |
| `TRACE_EVIDENCE` | Every published metric has `evidence_id` |

Publication tiers:

* `tier_a_publish` — core keys complete + accounting checks pass
* `tier_b_flagged` — publishable with explicit `validation_status=flagged`
* `tier_c_withheld` — must not be served as canonical truth

## 7.6 Version Control Layer

Responsible for:

* Historical revisions
* Restatements
* Version history
* Difference tracking
* Audit history

Rules:

* Same `(ticker, statement_type, period_end)` new content ⇒ `version += 1`
* Prior versions retained forever
* Restatement detection: material metric delta vs prior published version ⇒ `restatement=true` + diff record

## 7.7 Financial Warehouse

Canonical storage.

Every downstream system reads exclusively from this layer via FSE read APIs / Python façades.

Write path is internal to FSE only.

## 7.8 Derived Metrics Engine

Computes (non-exhaustive):

* ROE / ROCE
* Margins
* Ratios
* Valuation inputs
* Working capital metrics
* Forecast inputs (historical actuals only)

**Derived metrics never overwrite reported values.** They live under `derived/` namespace or separate derived documents with `derived=true`.

---

# 8. Consumers

Consumers include:

* Valuation Engine
* Forecast Engine
* Research Engine
* Company Memory
* Screeners
* Portfolio Intelligence
* Risk Engine
* Ask AGIB
* Research Notes
* Public APIs

Consumers are **read-only**.

They cannot modify financial data.

### Anti-bypass rule (enforce in code review)

Prohibited:

* Direct PDF/XBRL parsing inside Ask AGIB
* Direct XBRL parsing inside valuation models
* Independent financial collectors inside research modules
* Financial calculations that redefine reported line items outside FSE

Allowed:

* Consumer-local presentation formatting
* Consumer-local model assumptions that cite FSE inputs with lineage

---

# 9. Separation of Responsibilities

| Role | May do | Must not do |
| --- | --- | --- |
| Collectors | Discover/download/store raw | Parse business meaning, validate accounting, publish |
| Parsers / Extractors | Structured values + confidence | Synonym policy, ratios, publish |
| Normalizers | Canonical names/units/periods | Accounting validation edits, derived ratios |
| Validators | Status + issues | Mutate metric values |
| Warehouse | Store/serve canonical truth | Consumer-specific transforms |
| Consumers | Read published warehouse | Download/parse filings independently |

Responsibilities must never overlap.

---

# 10. Financial Integrity Rules

The engine must guarantee:

* No fabricated values
* No silent corrections
* No hidden transformations
* No loss of history
* No duplicate canonical metrics
* No direct edits of published statements
* No consumer-specific logic inside warehouse writes

---

# 11. Engineering Constraints

The Financial Statements Engine must be:

* Stateless where practical
* Idempotent
* Checkpointed
* Resumable
* Horizontally scalable
* Fault tolerant
* Observable
* Deterministic

Every processing stage must be independently retryable.

### Determinism

Given the same raw evidence bytes + extractor version + registry version, normalized output must be byte-stable for equal inputs (JSON key-sorted fingerprints).

---

# 12. Observability

Every processing stage exposes:

* Runtime
* Latency
* Success Rate
* Failure Rate
* Retry Count
* Coverage
* Freshness
* Queue Depth
* Validation Rate
* Throughput

These metrics must be visible within Mission Control via:

* `GET /v1/financial-statements/health`
* `GET /v1/financial-statements/dashboard`
* Soft export into Mission Control hardening/observability panels (additive; do not redefine MC contracts)

---

# 13. Canonical Source Rule

The Financial Warehouse is the only approved financial source.

All financial consumers must use the canonical warehouse through FSE façades:

* Python: `financial_statements_engine.production.get_statements(...)`
* HTTP: `/v1/financial-statements/...`

`earnings_intelligence` remains available during migration as an extraction/compatibility façade, but **new consumer code must call FSE**.

---

# 14. Quality Objectives

| Metric | Target |
| --- | --- |
| Annual statement completeness | >99% |
| Quarterly statement completeness | >98% |
| Validation success | >99.5% |
| Duplicate financial facts | <0.1% |
| Restatement detection | 100% |
| Source traceability | 100% |
| Version preservation | 100% |
| Canonical consistency | 100% |

Coverage-before-depth rollout target (v1):

* Universe: Nifty 500 (then IC-10 gold continuously)
* Depth gate: ≥5 fiscal years annual + ≥8 quarters where filings exist
* Deep history (>10y) is phase-2 after coverage SLOs green

---

# 15. Success Definition

The Financial Statements Engine is considered production-ready only when:

* Every financial figure is traceable to source evidence.
* Every published statement has passed validation or is explicitly flagged with validation status.
* Every revision is preserved and auditable.
* All downstream consumers read exclusively from the Financial Warehouse.
* Mission Control exposes complete operational health, coverage, freshness, and quality metrics.
* The platform can scale to additional companies, reporting standards, and financial metrics without redesigning the core architecture.

---

# 16. Canonical Metric Registry (v1)

**Authoritative service (FSE-03):** `financial_statements_engine/metric_registry/`  
Compatibility façade: `financial_statements_engine/registry.py` (do not add new metrics here).

See [FSE-03](FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md) for the full CFDM and Appendix A dictionary.

### Income statement (canonical)

`revenue`, `other_income`, `total_income`, `cogs`, `employee_cost`, `operating_expenses`, `finance_cost`, `depreciation`, `ebitda`, `ebit`, `profit_before_tax`, `tax_expense`, `net_income`, `pat_owners`, `eps_basic`, `eps_diluted`

### Balance sheet (canonical)

`total_assets`, `current_assets`, `non_current_assets`, `cash`, `total_equity`, `equity_share_capital`, `equity_owners`, `reserves`, `face_value`, `shares_outstanding`, `deposits`, `total_liabilities`, `current_liabilities`, `non_current_liabilities`, `total_debt`, `working_capital`

### Cash flow (canonical)

`operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `free_cash_flow`, `capex`, `net_cash_change`

### Synonym policy

* Metric Registry maps extractor-local and legacy pack keys → canonical
* Legacy P2.1 key `revenue_from_operations` **must** map to `revenue`
* Legacy `pat` / `pbt` map to `net_income` / `profit_before_tax`
* Adding a new synonym requires a Metric Registry version bump; ad-hoc aliases in consumers are forbidden

---

# 17. Public Interfaces

## 17.1 CLI

```bash
cd intelligence-engine
export PYTHONPATH=.

python -m financial_statements_engine --health
python -m financial_statements_engine --dashboard
python -m financial_statements_engine TCS
python -m financial_statements_engine TCS --publish
python -m financial_statements_engine --coverage nifty500
```

## 17.2 HTTP APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/financial-statements/health` | Engine health + layer status |
| GET | `/v1/financial-statements/dashboard` | Coverage / freshness / validation metrics |
| GET | `/v1/financial-statements/{ticker}` | Published statements pack for ticker |
| POST | `/v1/financial-statements/ingest` | Run discover→publish pipeline for ticker |
| GET | `/v1/financial-statements/{ticker}/versions` | Version history |
| GET | `/v1/financial-statements/{ticker}/evidence/{evidence_id}` | Raw evidence metadata (not silent rewrite) |

## 17.3 Python façade

```python
from financial_statements_engine.production import (
    health,
    dashboard,
    get_statements,
    ingest_and_publish,
    coverage_report,
)
```

Return objects must include:

* `engine`, `version`, `workstream_id`
* `publication_status` / `validation_status`
* `issues_recommendations: false`
* no BUY/SELL fields

---

# 18. Storage Layout

Default root (overridable via `FSE_STORE_ROOT`):

```text
$FSE_STORE_ROOT/
  raw/<ticker>/<evidence_id>.<ext>
  raw_meta/<ticker>/<evidence_id>.json
  extracted/<ticker>/<evidence_id>.json
  normalized/<ticker>/<period_end>/<statement_type>.json
  validated/<ticker>/<period_end>/<statement_type>.json
  versions/<ticker>/<statement_type>/<period_end>/v<N>.json
  published/<ticker>/latest.json
  derived/<ticker>/latest.json
  indexes/coverage.json
  indexes/freshness.json
  observability/metrics.jsonl
```

Warehouse read path prefers `published/`, with HD `financials_*` sync for platform compatibility.

---

# 19. Migration Plan (from P2.1)

| Phase | Work |
| --- | --- |
| M0 | Land this spec + package skeleton + health/dashboard + registry |
| M1 | Raw evidence + extraction adapter wrapping `earnings_intelligence` |
| M2 | Normalize + canonical statement builder using registry |
| M3 | Validation + versioning + publish gate |
| M4 | Warehouse read façade; dual-write to HD `financials_*` |
| M5 | Repoint Company Memory / CID soft-attach / Valuation to FSE reads |
| M6 | Deprecate direct consumer use of `earnings_intelligence` (keep as extractor) |

During M0–M4, FSE may call `earnings_intelligence` internally. Consumers must still migrate to FSE read APIs.

---

# 20. Test Requirements

Minimum tests (package must keep green):

1. `health()` returns `status=ok`, workstream `FSE-01`
2. Registry maps `revenue_from_operations` → `revenue`
3. Registry has unique canonical names (no duplicates)
4. Lifecycle rejects publish when `TRACE_EVIDENCE` fails
5. Version increment preserves prior version files
6. Idempotent re-ingest of identical evidence does not create duplicate published facts
7. No recommendation / BUY / SELL keys in public payloads

Gold entities for continuous checks: TCS, HDFCBANK, RELIANCE, NTPC, TATAMOTORS/TMPV.

---

# 21. Non-Goals (v1)

* LLM summarization of filings
* BUY/SELL / portfolio advice
* Replacing Decision Engine scoring
* Building a second XBRL parser outside extraction adapters
* Silent repair of accounting identities

---

# 22. Architecture Principles Summary

1. **Evidence before data** — every figure originates from verifiable source evidence.
2. **Layers over shortcuts** — data flows through immutable architectural layers.
3. **Canonical truth** — one normalized financial representation for all consumers.
4. **Immutable history** — never overwrite; always version.
5. **Validation before publication** — quality gates precede downstream use.
6. **Separation of concerns** — collectors, parsers, validators, storage, and consumers each have a single responsibility.
7. **Observability by default** — every stage is measurable and monitorable.
8. **Institutional quality over implementation speed** — correctness, auditability, and reproducibility take precedence over throughput.

---

# 23. Implementation Checklist (for coding agents)

Implement in order; do not skip layers:

- [ ] `schema.py` constants + statuses
- [ ] `registry.py` canonical + synonyms
- [ ] `production.health` / `dashboard`
- [ ] CLI `__main__.py`
- [ ] HTTP routes under `/v1/financial-statements/*`
- [ ] `raw_evidence.py` immutable store + checksums
- [ ] `extraction/nse_xbrl.py` adapter (wrap P2.1)
- [ ] `normalize.py` registry + units
- [ ] `canonical.py` statement documents
- [ ] `validate.py` checks + tiers
- [ ] `versioning.py` diffs + restatements
- [ ] `warehouse.py` publish + read
- [ ] `derived.py` ratios without overwriting reported
- [ ] `observability.py` metrics JSONL
- [ ] dual-write sync to HD financial series
- [ ] tests listed in §20
- [ ] consumer migration notes in package README

**Acceptance for M0 (this PR):** spec committed, package importable, health/dashboard/CLI/API wired, registry uniqueness tests green, no Decision Engine / governance edits.
