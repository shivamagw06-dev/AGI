# FSE-05 — Validation & Financial Quality Engine (VFQE)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-05 |
| **Package** | `intelligence-engine/financial_statements_engine/validation/` |
| **Depends on** | FSE-01…FSE-04.3 |
| **Consumes** | Canonical Drafts · Parse Manifests · Evidence Coverage Matrices · Metric Registry |
| **Produces** | Validation Reports · Financial Quality Scores · Validated Financial Facts |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** VFQE is a **deterministic accounting engine**, not an AI reasoning system. It never reads PDFs/HTML/XBRL/raw evidence. It never reparses. It never modifies Canonical Drafts.

### Document series

| ID | Role |
| --- | --- |
| FSE-01…04.3 | Platform → evidence → schema → parse → coverage → PCC |
| **FSE-05** | **Validation & Financial Quality Engine** |
| FSE-06 | [Financial Warehouse](FSE_06_FINANCIAL_WAREHOUSE.md) |
| FSE-07…10 | Derived Metrics · Forecast · Time-Series · Intelligence APIs |

---

# 1. Mission

Convert Canonical Drafts into Validated Financial Facts.

* Detect structural, accounting, temporal, and statistical issues
* Produce deterministic validation results and Financial Quality Scores
* **Only validated facts may enter the Financial Warehouse**

---

# 2. Architecture

```text
Canonical Draft
+ Parse Manifest
+ Evidence Coverage Matrix
+ Metric Registry
        ↓
Validation Pipeline (independent rule engines)
        ↓
Validation Report
        ↓
Financial Quality Score
        ↓
Approval Decision
        ↓
Validated Financial Facts → Financial Warehouse
```

---

# 3. Principles

* Observational — never invents or corrects values
* Never overwrites parser output / Canonical Drafts
* Never reparses documents
* Explicit pass/fail; every rule reproducible and traceable
* Fully versioned; audit history preserved

---

# 4. Pipeline stages

1. Input Integrity  
2. Structural Validation  
3. Accounting Validation  
4. Cross-Statement Validation  
5. Temporal Validation  
6. Statistical Validation  
7. Business / Sector Rule Validation  
8. Quality Scoring  
9. Approval Decision  

---

# 5. Severity & approval

| Severity | Default publication impact |
| --- | --- |
| INFO | None |
| WARNING | Allowed (`APPROVED_WITH_WARNINGS`) |
| ERROR | Blocks when configured (`block_on_error`) |
| CRITICAL | Always blocks |

Approval states: `APPROVED` · `APPROVED_WITH_WARNINGS` · `REJECTED` · `QUARANTINED`

---

# 6. Quality score

Deterministic components (configurable weights):

Structural · Accounting Integrity · Coverage Quality · Temporal Consistency · Statistical Health · Parser Confidence  

Grades: `A+` · `A` · `B` · `C` · `D` · `Fail`

---

# 7. Package layout

```text
validation/
  pipeline.py
  structural/
  accounting/
  cross_statement/
  temporal/
  statistical/
  sector_rules/
  scoring/
  approval/
  reporting/
  publish.py
  production.py
```

Sector rules are isolated from core accounting rules.

---

# 8. Success criteria

* Every Canonical Draft receives a deterministic validation result
* Only Validated Financial Facts enter the warehouse
* Every decision is fully traceable and replayable
* Mission Control exposes validation health
* Downstream engines consume Validated Financial Facts unless in debug mode

---

**Acceptance:** FSE-05 importable; draft validation never mutates drafts; approval gates warehouse writes; scoring explainable; tests green for integrity/accounting/statistical/approval paths.
