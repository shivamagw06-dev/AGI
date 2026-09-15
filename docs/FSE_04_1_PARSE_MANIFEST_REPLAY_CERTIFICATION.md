# FSE-04.1 — Parse Manifest, Replay & Certification Framework

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-04.1 |
| **Extends** | [FSE-04](FSE_04_PARSING_NORMALIZATION_ENGINE.md) (does not change PNE architecture) |
| **Package** | `intelligence-engine/financial_statements_engine/parsing/quality/` |
| **Depends on** | FSE-01…FSE-04 |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** Not a new parser. This is the operational framework that makes every parse explainable, replayable, auditable, benchmarked, versioned, and comparable — for years.

### Implementation pause recommendation

Implement **FSE-01 → FSE-04.3** before starting **FSE-05**. Validation depends on stable, deterministic, certifiable canonical drafts plus an extraction coverage audit and a permanent golden corpus. Parsing churn after FSE-05 starts creates avoidable rework.

### Document series

| ID | Role |
| --- | --- |
| FSE-01…04 | Platform → evidence → schema → parse |
| **FSE-04.1** | **Parser quality / audit / replay / certification** |
| FSE-04.2 | [Evidence Coverage Matrix](FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md) — extraction audit |
| FSE-04.3 | [Production Certification Corpus](FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md) — golden dataset |
| FSE-05 | [Validation & Financial Quality Engine](FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) |

---

# 1. Mission

Every parsed document must be:

* Explainable
* Replayable
* Auditable
* Benchmarked
* Versioned
* Comparable

Every parser release must prove it is better than the previous release before entering production.

---

# 2. Architecture

```text
Raw Evidence
      ↓
Parser (FSE-04)
      ↓
Parse Manifest          ← FSE-04.1 (immutable audit record)
      ↓
Evidence Coverage Matrix ← FSE-04.2 (extraction audit)
      ↓
Canonical Draft
      ↓
Validation Engine (FSE-05)
      ↓
Financial Warehouse
```

**No canonical draft exists without a Parse Manifest.**

---

# 3. Parse Manifest

Every parsing operation produces one immutable Parse Manifest.

### Required fields

| Field | Notes |
| --- | --- |
| `manifest_id` | Stable id |
| `draft_id` | Links to draft artifact |
| `document_hash` | SHA-256 of raw bytes |
| `company_id` | CFDM company id |
| `ticker` | |
| `parser_name` | parser_id |
| `parser_version` | |
| `schema_version` | Schema Evolution version |
| `metric_registry_version` | |
| `pne_version` | FSE-04 engine version |
| `parse_timestamp` | |
| `processing_time_ms` | |
| `document_type` | |
| `source` | |
| `reporting_period` | period_end / kind / consolidation |
| `currency_detected` | |
| `unit_detected` | dominant / per-metric summary |
| `sections_found` | |
| `metrics_extracted` | count + ids |
| `metrics_unknown` | count + labels |
| `metrics_missing` | expected-but-absent (when reference provided) |
| `warnings` | |
| `errors` | |
| `confidence` | multi-stage object (§4) |
| `hierarchy_fingerprint` | |
| `deterministic_fingerprint` | from FSE-04 |
| `lineage_root_id` | |
| `replay_of` | prior manifest_id \| null |
| `immutable` | always true after write |

Storage:

```text
$FSE_STORE_ROOT/parsing/manifests/<ticker>/<manifest_id>.json
$FSE_STORE_ROOT/parsing/drafts/<ticker>/<draft_id>.json   # never overwritten; new draft_id per parse
```

Module: `parsing/quality/manifest.py`

---

# 4. Multi-Stage Confidence

Replace a single score with four independent stages:

| Stage | Key | Meaning |
| --- | --- | --- |
| Extraction | `extraction` | Bytes → labeled values |
| Normalization | `normalization` | Labels → canonical metrics |
| Structural | `structural` | Sections/hierarchy integrity |
| Overall | `overall` | Aggregate (documented formula) |

Failures must be attributable to a stage (`confidence.failure_stage`).

Default overall (v1):

```text
overall = 0.4*extraction + 0.4*normalization + 0.2*structural
```

Module: `parsing/quality/confidence.py`

---

# 5. Hierarchical Statement Tree

Preserve document hierarchy **before** flattening.

Example:

```text
Income Statement
  Revenue
    Revenue From Operations
      Domestic Revenue
      Export Revenue
→ Canonical Metrics (flat)
```

Rules:

* Hierarchy remains queryable (`statement_tree`)
* Flattening never destroys parent-child relationships
* Tree nodes store `label`, `canonical` (nullable), `children`, `value` (nullable)

Module: `parsing/quality/hierarchy.py`

---

# 6. Unknown Metric Review

Unknown labels are never discarded.

Workflow:

```text
Unknown Metric → Review Queue → Engineering Approval
  → Metric Registry Update → Schema Version Increment
  → Future Automatic Recognition
```

Queue record fields: `label`, `ticker`, `evidence_id`, `manifest_id`, `context`, `status` (`open`/`approved`/`rejected`), `proposed_canonical`, `reviewed_at`.

Module: `parsing/quality/unknown_queue.py`

---

# 7. Parser Replay Engine

Input: Raw Evidence + Parser Version + Schema Version  
Output: New Canonical Draft + Replay Diff + Replay Report

Rules:

* Never modify raw evidence
* Never overwrite historical drafts or manifests
* Always create new `manifest_id` / `draft_id` with `replay_of` set

Module: `parsing/quality/replay.py`

---

# 8. Diff Engine

Compare Old Draft ↔ New Draft:

* Added / removed metrics
* Changed values
* Changed labels
* Changed structure (hierarchy fingerprint)
* Confidence changes

Diff attaches to replay reports and certification runs.

Module: `parsing/quality/diff.py`

---

# 9. Event Versioning

All events are versioned. Consumers must not depend on unversioned names.

| Event | Purpose |
| --- | --- |
| `parse.completed.v1` | Manifest + draft ready |
| `parse.failed.v1` | Classified failure |
| `parse.quarantined.v1` | Unsupported |
| `draft.created.v1` | New draft artifact |
| `draft.updated.v1` | New draft superseding prior (pointer only; history kept) |
| `schema.updated.v1` | Registry / schema evolution bump |
| `unknown_metric.queued.v1` | Review queue insert |
| `parser.certified.v1` | Certification pass |
| `parser.certification_failed.v1` | Certification fail |

Legacy unversioned `parse.*` aliases may be emitted alongside v1 during migration, then removed.

Module: update `events.py`

---

# 10. Lineage Graph

Every metric stores complete lineage:

```text
Raw Document → Section → Table → Row → Cell
  → Metric → Canonical Draft → Validated Fact → Derived Metric → Consumer
```

v1 stores lineage nodes on each draft fact + manifest `lineage_root_id`.  
FSE-05/09 attach validated/consumer hops later without rewriting parse lineage.

Module: `parsing/quality/lineage.py`

---

# 11. Parser Certification

Every parser release must pass certification against a reference dataset:

* Reference filings (raw bytes or fixtures)
* Expected metrics / hierarchy / confidence floors / structure

Only certified parser versions may be marked production-ready.

Module: `parsing/quality/certification.py`  
Fixtures: `parsing/quality/certification_fixtures/`

---

# 12. Benchmark Suite

Benchmark classes:

* NSE XBRL, BSE filings, Annual / Quarterly reports
* Complex tables, Segment reporting, Restated statements
* Sectors: Large FI, Manufacturing, IT, Banks, NBFCs, Insurance

Each run records: Accuracy, Precision, Recall, Latency, Coverage, Failure Rate, Unknown Metrics.

Module: `parsing/quality/benchmarks.py`

---

# 13. Quality Gates

| Gate | Threshold |
| --- | --- |
| Metric Extraction Accuracy | >99.5% |
| Canonical Mapping Accuracy | >99.5% |
| Unknown Metric Rate | <0.5% |
| Hierarchy Preservation | 100% |
| Replay Determinism | 100% |
| Duplicate Draft Rate | 0% (same manifest_id never rewritten) |
| Traceability | 100% |
| Benchmark Pass Rate | 100% |

Any failed gate ⇒ cannot deploy (`production_eligible: false`).

Module: `parsing/quality/gates.py`

---

# 14. Mission Control Surfaces

Expose:

* Parser health / version / certification status
* Replay queue
* Unknown metric queue
* Benchmark results
* Latency / coverage / confidence / failure distributions
* Event throughput

APIs:

* `GET /v1/financial-statements/parsing/quality/health`
* `GET /v1/financial-statements/parsing/quality/dashboard`
* `GET /v1/financial-statements/parsing/manifests/{ticker}`
* `POST /v1/financial-statements/parsing/replay`
* `GET /v1/financial-statements/parsing/unknown-metrics`
* `POST /v1/financial-statements/parsing/certify`
* `POST /v1/financial-statements/parsing/benchmark`

---

# 15. Engineering Principles

* Never modify raw evidence
* Never overwrite canonical drafts or manifests
* Never remove history
* Every parser release is reproducible, benchmarked, explainable, replayable, certifiable
* Institutional reliability is mandatory

---

# 16. Success Criteria

* Every parsing operation produces an immutable Parse Manifest
* Every parser version is benchmarked before deployment eligibility
* Historical evidence can be replayed at any time
* Unknown metrics continuously feed the review → registry loop
* Mission Control exposes complete parser health
* Every canonical draft is fully traceable to source
* Parser regressions are detected before production deployment

---

# 17. Module Mapping

```text
financial_statements_engine/parsing/quality/
  __init__.py
  schema.py
  confidence.py
  hierarchy.py
  lineage.py
  manifest.py
  unknown_queue.py
  diff.py
  replay.py
  certification.py
  benchmarks.py
  gates.py
  production.py
  certification_fixtures/
    README.md
    tcs_annual_min.json
    expected_tcs_annual_min.json
```

Integration: `parsing/pipeline.py` **must** call `manifest.build_and_store` before returning success; drafts get unique `draft_id`.

---

# 18. Test Requirements

1. Successful parse always yields `manifest_id` + immutable file
2. Re-parse creates new draft/manifest; prior files untouched
3. Multi-stage confidence present with four keys
4. Hierarchy tree preserves parent-child for nested labels
5. Unknown labels enter review queue
6. Replay produces diff report without mutating raw evidence
7. Certification fixture pass/fail gates work
8. Versioned events `parse.completed.v1` emitted
9. `production_eligible` false when a gate fails
10. No BUY/SELL fields

---

# 19. Implementation Checklist

- [ ] Spec committed
- [ ] Versioned events in `events.py`
- [ ] quality/* modules
- [ ] Pipeline integration (manifest mandatory)
- [ ] CLI + HTTP
- [ ] Certification fixtures + tests
- [ ] Series links updated

**Acceptance:** FSE-04.1 importable; every parse has a manifest; replay/diff/unknown-queue/certification/gates tests green.
