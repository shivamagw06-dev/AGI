# FSE-04 — Parsing & Normalization Engine

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-04 |
| **Depends on** | [FSE-01](FSE_01_FINANCIAL_STATEMENTS_ENGINE.md), [FSE-02](FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md), [FSE-03](FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md) |
| **Package** | `intelligence-engine/financial_statements_engine/parsing/` |
| **Schema Evolution** | `intelligence-engine/financial_statements_engine/schema_evolution/` |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine formulas · Institutional Gate · Evaluation Lab · IAT · Mission Control contracts |

> **Criticality:** Downloading filings is relatively easy. Accurately extracting, normalizing, and reconciling them across thousands of companies is where most platforms fail. This engine must be deterministic, traceable, and never invent values.

### Document series

| ID | Document | Role |
| --- | --- | --- |
| FSE-01 | Architecture & Principles | What the architecture is |
| FSE-02 | Data Sources & Collection Pipeline | How data enters |
| FSE-03 | Canonical Financial Data Model & Schema | Authoritative representation |
| **FSE-04** | **Parsing & Normalization Engine** | **Raw evidence → canonical statements** |
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

The Parsing & Normalization Engine (PNE) transforms raw financial evidence into structured, standardized, machine-readable financial data.

The engine is responsible for:

* Extracting financial values
* Understanding document structure
* Mapping financial concepts
* Standardizing terminology
* Normalizing currencies and units
* Producing canonical statements for validation

The Parsing & Normalization Engine **does not** validate accounting correctness. Validation belongs exclusively to the Validation Engine (FSE-05).

---

# 2. Objectives

The engine shall:

* Parse multiple document formats.
* Preserve every extracted value.
* Capture document hierarchy.
* Normalize financial terminology.
* Detect units and currencies.
* Produce deterministic output.
* Preserve traceability.
* Never fabricate missing information.

---

# 3. Supported Input Formats

The engine must support:

* XBRL
* iXBRL
* PDF
* HTML
* Excel
* CSV
* JSON
* XML

Every parser implements a common interface (`parsing/base.py`).

v1 priority order for production coverage:

1. XBRL / iXBRL / XML (NSE IND-AS via existing extraction adapter)
2. HTML (exchange filings)
3. JSON (structured intermediate packs)
4. PDF / Excel / CSV (stubs + quarantine until dedicated parsers land)

---

# 4. Parsing Pipeline

```text
Raw Evidence
      ↓
Document Identification
      ↓
Document Parser
      ↓
Structure Detection
      ↓
Field Extraction
      ↓
Metric Mapping          ← Metric Registry + Schema Evolution
      ↓
Unit Detection
      ↓
Currency Detection
      ↓
Normalization
      ↓
Canonical Statement     ← CFDM builders (draft; not warehouse-published)
      ↓
Emit parse.completed    ← Evidence Event Bus (FSE-05 subscribes)
```

Each stage is independently testable.

Collectors (FSE-02) never call this pipeline inline. PNE subscribes to `evidence.stored`.

---

# 5. Parser Selection

The engine automatically determines:

* document type
* filing type
* exchange
* reporting standard
* parser version

Unsupported formats are quarantined for manual review (`parsing/quarantine.py`).

Module: `parsing/identify.py`, `parsing/registry.py`

---

# 6. Structure Detection

Before extracting values, identify:

* Income Statement
* Balance Sheet
* Cash Flow
* Notes
* Segment Reporting
* Share Capital
* EPS
* Auditor Information

Section boundaries must be preserved in extraction metadata.

Module: `parsing/structure.py`

---

# 7. Extraction Rules

Extract:

* Labels
* Values
* Tables
* Footnotes
* Dates
* Units
* Currency
* Metadata

Unknown fields are retained under `unknown_fields`.

**Nothing is discarded.**

---

# 8. Normalization

Incoming labels are converted into canonical metrics via FSE-03 Metric Registry.

Example:

```text
Revenue From Operations → revenue
Net Profit → net_income
Finance Costs → finance_cost
```

The normalization dictionary is versioned and centrally managed (Metric Registry + Schema Evolution).

**No parser may define its own synonym mappings.**

---

# 9. Synonym Engine

Every synonym maps to one canonical metric.

```text
Sales / Revenue / Revenue From Operations / Net Sales → revenue
```

Implementation: call `metric_registry.resolve` only. Private parser maps are forbidden (enforced in code review + tests).

---

# 10. Unit Normalization

Automatically detect units / scale / decimal precision.

Examples: ₹, ₹ Lakhs, ₹ Crores, Millions, Billions, Thousands.

Convert into canonical storage units (`normalized_value` in ones) while preserving `reported_value` + `scale`.

Module: `parsing/units.py`

---

# 11. Currency Normalization

Detect: INR, USD, EUR, GBP, JPY, Others.

Store:

* `original_currency`
* `canonical_currency` (default reporting currency from Company / INR for India v1)
* `fx_note` / conversion timestamp **only if** FX applied

**No FX conversion is performed unless explicitly required by a downstream consumer request.** Default: store original currency; set `canonical_currency = original_currency` when no FX.

Module: `parsing/currency.py`

---

# 12. Period Recognition

Recognise: Annual, Quarterly, Half-Yearly, Nine Months, TTM (if reported), Standalone, Consolidated, Restated.

**Never infer a reporting period** when absent — leave null and flag `period_unresolved`.

Module: `parsing/period.py`

---

# 13. Missing Values

Missing values are stored explicitly as JSON `null`.

Never use:

* `0` as a stand-in for missing
* Estimated values
* Previous values
* Interpolation

---

# 14. Duplicate Detection

Detect duplicate rows / metrics / repeated statements / repeated filings within a parse.

Duplicates are flagged in parse metadata before canonical handoff (`duplicate_flags`). FSE-05 decides publication impact.

Module: `parsing/duplicates.py`

---

# 15. Traceability

Every extracted metric stores:

* Source document / `evidence_id`
* Page number (when available)
* Table / row / column identifiers
* Parser version
* Extraction timestamp
* Confidence score

Every value must be explainable.

---

# 16. Parser Confidence

Every extracted metric receives:

* `extraction_confidence`
* `normalization_confidence`
* `overall_confidence`

Low-confidence values are flagged for validation (`confidence_flagged: true` when overall < 0.7).

---

# 17. Parser Registry

Every parser defines:

| Field | Purpose |
| --- | --- |
| `parser_id` | Stable id |
| `supported_formats` | xbrl, html, … |
| `version` | Parser semver |
| `supported_exchanges` | NSE, BSE, … |
| `supported_standards` | IND_AS, IFRS, … |
| `output_schema` | `cfdm_statement_draft_v1` |
| `fallback_parser` | optional parser_id |

Module: `parsing/registry.py`

---

# 18. Error Handling

Errors are classified:

* Parse Failure
* Structure Failure
* Unsupported Format
* Missing Sections
* Corrupt Document
* Encoding Error

Errors never terminate the broader collection pipeline. Documents enter retry or review/quarantine queues.

---

# 19. Determinism

The same document processed twice using the same parser version + registry version + schema-evolution version must produce identical canonical output (key-sorted JSON fingerprint).

Non-deterministic parsing is prohibited (no wall-clock in fact payloads except explicit metadata timestamps that are excluded from fingerprints).

---

# 20. Performance

The engine must support:

* Parallel document parsing
* Independent parser workers
* Checkpointing
* Incremental processing
* Resume after interruption
* Parser isolation (one document failure ≠ process crash)

v1: in-process worker pool interface; durable checkpoints under `$FSE_STORE_ROOT/parsing/checkpoints/`.

---

# 21. Output

The Parsing Engine publishes:

* Canonical Statement **drafts** (CFDM)
* Parser Metadata
* Normalization Metadata
* Confidence Scores
* Extraction Logs
* Event: `parse.completed` / `parse.failed` / `parse.quarantined`

**Nothing is written directly to the Financial Warehouse until validation succeeds (FSE-05).**

Draft artifacts live under:

```text
$FSE_STORE_ROOT/parsing/drafts/<ticker>/<evidence_id>.json
$FSE_STORE_ROOT/parsing/logs/<ticker>/<evidence_id>.jsonl
```

---

# 22. Observability

Expose:

* Documents processed
* Average parse time
* Parser success / failure rate
* Normalization accuracy proxy (mapped / unmapped ratio)
* Unknown metrics
* Confidence distribution
* Queue depth
* Retry rate

Surfaces: `GET /v1/financial-statements/parsing/health|dashboard`

---

# 23. Quality Targets

| Metric | Target |
| --- | --- |
| Parsing success | >99% |
| Deterministic output | 100% |
| Unknown metric rate | <1% |
| Unit detection accuracy | >99.5% |
| Currency detection accuracy | 100% |
| Canonical mapping accuracy | >99% |
| Traceability | 100% |

---

# 24. Engineering Rules

The Parsing & Normalization Engine shall never:

* Invent values
* Guess missing metrics
* Modify accounting values
* Correct financial statements
* Calculate derived metrics
* Merge reporting periods
* Merge standalone and consolidated reports
* Remove source traceability
* Write published warehouse facts (FSE-05 gate)

Its sole responsibility is to transform source documents into standardized canonical statement **drafts**.

---

# 25. Schema Evolution Engine (architect recommendation)

Financial reporting standards evolve (new XBRL taxonomies, IFRS/Ind AS amendments, new disclosures).

FSE-04 includes a **Schema Evolution Engine** that records versioned mapping knowledge beyond static synonyms:

| Field | Purpose |
| --- | --- |
| `canonical_metric` | FSE-03 metric id |
| `synonyms` | labels / tags |
| `reporting_standards` | IND_AS, IFRS, US_GAAP, … |
| `taxonomy` | e.g. `nse_indas_integrated_filing` |
| `taxonomy_version` | string |
| `effective_from` | date |
| `effective_to` | date \| null |
| `status` | `active` \| `deprecated` |
| `replaced_by` | metric id \| null |
| `parent_metric` | hierarchical parent \| null |
| `children` | hierarchical children |

Parsers resolve labels through:

```text
Schema Evolution (as-of filing date + standard)
        ↓
Metric Registry (canonical authority)
```

This allows new standards/disclosures without redesigning PNE or the warehouse.

Package: `financial_statements_engine/schema_evolution/`

Version: `schema-evolution-v1.0.0`

---

# 26. Module Mapping

```text
financial_statements_engine/parsing/
  __init__.py
  schema.py
  base.py              # Parser protocol / common interface
  registry.py          # parser registry
  identify.py          # document identification
  structure.py         # section detection
  extract.py           # field extraction orchestration
  units.py
  currency.py
  period.py
  duplicates.py
  normalize_stage.py   # metric map + unit/currency (uses Metric Registry)
  pipeline.py          # full PNE pipeline
  quarantine.py
  worker.py            # parallel / checkpoint helpers
  subscriber.py        # Evidence Event Bus subscription
  production.py
  parsers/
    xbrl.py            # wraps extraction/nse_xbrl + structured bytes
    html.py
    json_pack.py       # structured JSON packs / fixtures
    pdf.py             # stub → quarantine
    excel.py           # stub → quarantine
    csv_parser.py      # stub → quarantine
    xml_generic.py

financial_statements_engine/schema_evolution/
  __init__.py
  schema.py
  store.py             # versioned mapping records
  service.py           # resolve_label(as_of, standard, label)
  seed.py              # initial IND-AS / NSE mappings
  production.py
```

---

# 27. Event Catalogue (PNE)

| Event | When |
| --- | --- |
| `parse.started` | Pipeline begins for evidence_id |
| `parse.completed` | Draft canonical statements written |
| `parse.failed` | Classified failure |
| `parse.quarantined` | Unsupported / needs review |

FSE-02 bus must allow these event types (extend `collection/schema.py` EVENT_TYPES or use a shared `events.py`). Prefer extending the shared bus event allow-list in `collection/schema.py` **or** introduce `financial_statements_engine/events.py` as shared catalogue — implement shared catalogue in this PR to avoid FSE-02-only coupling.

---

# 28. Public Interfaces

## CLI

```bash
python -m financial_statements_engine --parsing-health
python -m financial_statements_engine --parsing-dashboard
python -m financial_statements_engine --parse-evidence TICKER EVIDENCE_ID
python -m financial_statements_engine --parse-bytes TICKER --format xbrl --file path
python -m financial_statements_engine --schema-evolution-health
```

## HTTP

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/financial-statements/parsing/health` | PNE health |
| GET | `/v1/financial-statements/parsing/dashboard` | Metrics |
| POST | `/v1/financial-statements/parsing/run` | Parse evidence / injected bytes |
| GET | `/v1/financial-statements/schema-evolution/health` | Schema evolution health |
| GET | `/v1/financial-statements/schema-evolution/resolve` | Label resolve as-of |

---

# 29. Test Requirements

1. Same XBRL/JSON bytes twice ⇒ identical draft fingerprint (determinism)
2. `Revenue From Operations` maps to `revenue` via registry (no parser-local map)
3. Missing value remains `null` (not `0`)
4. Unknown label retained in `unknown_fields`
5. Unsupported PDF quarantined (not warehouse-written)
6. Traceability: every mapped metric has `evidence_id`
7. Pipeline does not call warehouse `publish_statement`
8. Schema evolution resolves IND-AS synonym as-of date
9. Event bus emits `parse.completed`
10. No BUY/SELL fields

---

# 30. Implementation Checklist

- [ ] Shared event catalogue including parse.* events
- [ ] Parser interface + registry + identify
- [ ] XBRL/JSON parsers; PDF/Excel stubs → quarantine
- [ ] Structure / units / currency / period / duplicates stages
- [ ] Normalize stage via Metric Registry only
- [ ] Pipeline → CFDM draft facts/statements (not warehouse publish)
- [ ] Schema Evolution Engine seed + resolve
- [ ] Event Bus subscriber for `evidence.stored`
- [ ] CLI + HTTP + tests
- [ ] Series links updated

**Acceptance:** Spec committed; PNE importable; determinism + no-warehouse-write + registry-only mapping tests green.

---

# 31. Next

**FSE-05 — Validation & Financial Quality Engine** defines how canonical statement drafts are checked, reconciled, scored, and approved before entering the Financial Warehouse.
