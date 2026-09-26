# FSE-06 — Financial Warehouse (FWH)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-06 |
| **Package** | `intelligence-engine/financial_statements_engine/financial_warehouse/` |
| **Depends on** | FSE-01…FSE-05 |
| **Consumes** | Validated Financial Facts (FSE-05) only |
| **Serves** | DCF · Forecast · Screeners · Portfolio · Watchlists · Macro · Ask AGIB · Research · Company Memory · API |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** The Financial Warehouse is AGIB's permanent institutional repository for Validated Financial Facts. It is **not** a parser, **not** a validation engine, and never performs accounting validation. It is write-once, versioned, and auditable.

### Document series

| ID | Role |
| --- | --- |
| FSE-01…05 | Platform → evidence → schema → parse → coverage → PCC → validation |
| **FSE-06** | **Financial Warehouse** (immutable facts · versioning · restatements · contracts) |
| FSE-07 | Derived Metrics Engine |
| FSE-08 | Forecast & Estimates Engine |
| FSE-09 | Financial Time-Series & Revision Engine |
| FSE-10 | Financial Intelligence APIs |

> **Note:** Versioning & restatement (earlier series placeholder) are owned by FWH in this workstream.

---

# 1. Mission

* Store only Validated Financial Facts
* Never store unvalidated Canonical Drafts as production facts
* Maintain complete historical lineage
* Support versioning, restatements, replay, and audit
* Be the single source of truth for every financial consumer inside AGIB

---

# 2. Architecture

```text
Validated Financial Facts (FSE-05)
        ↓
Financial Warehouse Publisher
        ↓
Version Store · Historical Store · Indexes
        ↓
Data Contract Layer (v1, v2, …)
        ↓
Consumers (DCF, Forecast, Screener, Ask AGIB, …)
```

Write-once. Facts are never edited. Corrections always create new versions.

---

# 3. Design principles

Immutable · Deterministic · Auditable · Versioned · Traceable · Replayable · Backward compatible · Institutional grade

---

# 4. Warehouse content

Stores only:

Validated Financial Facts · Validation Metadata · Quality Score · Version Information · Lineage / Manifest / Coverage / Source References · Publication Metadata

**Never stores:** raw evidence · parser output · temporary drafts

---

# 5. Publication gate

Only `APPROVED` and `APPROVED_WITH_WARNINGS` facts may be published.

`REJECTED` and `QUARANTINED` remain outside the warehouse.

---

# 6. Versioning & restatements

* Facts are immutable; updates create new versions
* Historical versions remain queryable
* Restatements preserve originals and link replacement versions
* Views: Latest · Original · As Reported · As Restated

---

# 7. Time travel

Support: As Published · As Of Date · As Originally Filed · As Restated · As Validated  

Historical queries must always be reproducible.

---

# 8. Data Contract Layer

Consumers **must not** read warehouse tables/files directly.

```text
Financial Warehouse
        │
        ▼
Data Contracts (v1, v2, …)
        │
        ├── DCF Contract
        ├── Forecast Contract
        ├── Screener Contract
        ├── API Contract
        └── Ask AGIB Contract
```

Contracts are versioned, stable, and the only supported consumer interface.

---

# 9. Package layout

```text
financial_warehouse/
  publisher/
  versioning/
  restatements/
  storage/
  indexing/
  query/
  lineage/
  time_travel/
  contracts/
  observability/
  production.py
```

Storage and retrieval only — no accounting business logic.

---

# 10. Success criteria

* Permanent financial system of record
* Every published fact immutable and fully traceable
* Every historical version available
* Identical facts for identical queries
* Complete historical reconstruction of every published statement
* Only production source for structured financial data across AGIB

---

**Acceptance:** FWH importable; only validated facts publish; versions never overwritten; contracts serve consumers; time-travel/restatement APIs tested; Mission Control health green.
