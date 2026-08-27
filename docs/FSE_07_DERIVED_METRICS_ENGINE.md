# FSE-07 — Derived Metrics Engine (DME)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — implemented |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-07 |
| **Package** | `intelligence-engine/financial_statements_engine/derived_metrics/` |
| **Depends on** | FSE-01…FSE-06 |
| **Consumes** | Validated Financial Facts via Financial Warehouse (FSE-06) only |
| **Produces** | Versioned derived metrics + metric data contracts |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** Transform Validated Financial Facts into deterministic, versioned, reusable financial metrics. Not a parser, validator, or forecast engine. **No consumer calculates financial metrics independently.**

### Document series

| ID | Role |
| --- | --- |
| FSE-01…06 | Architecture → collection → model → parse → QA → coverage → PCC → validation → warehouse |
| **FSE-07** | **Derived Metrics Engine** |
| FSE-08 | Forecast & Estimates Engine |
| FSE-09 | Financial Time-Series & Revision Engine |
| FSE-10 | Financial Intelligence APIs |

---

# 1. Mission

* Compute institutional-grade derived financial metrics
* One canonical definition for every ratio
* Identical calculations for every downstream consumer
* Full lineage back to validated financial facts
* Publish via versioned data contracts

---

# 2. Architecture

```text
Validated Financial Facts (FWH)
        ↓
Dependency Resolver
        ↓
Formula Registry
        ↓
Calculation Engine
        ↓
Derived Metric Store (immutable versions)
        ↓
Publication Contracts
        ↓
Consumers (DCF · Forecast · Screener · Portfolio · Ask AGIB · API)
```

---

# 3. Design principles

Deterministic · Versioned · Immutable · Traceable · Replayable · Formula-driven · No duplicated business logic · Institutional consistency

---

# 4. Inputs (allowed)

Validated Financial Facts · Financial Warehouse · Validation Metadata · Version Metadata · Quality Scores · Restatement History · Time Travel Queries

**Never:** Raw Evidence · Canonical Drafts · Parser Output · Temporary Data

---

# 5. Formula Registry

Every metric is defined centrally (`formula_id`, `metric_name`, `version`, `expression`, `required_inputs`, `dependencies`, `sector_overrides`, `effective_date`, `status`, `owner`, `description`).

No formulas are hardcoded inside consumers. Seed catalogue lives in `derived_metrics/formula_registry/formulas.py`.

---

# 6. Calculation Engine

* Deterministic AST evaluator (no Python `eval`)
* Batch / incremental / single-company
* Historical & restatement replay via warehouse facts
* Rejects: division by zero, missing mandatory inputs, circular deps, prohibited negative denominators, overflow

---

# 7. Restatement handling

When a warehouse fact changes: detect affected metrics → recalculate only impacted metrics → create new versions → never overwrite history.

Hook: `financial_warehouse.restatements.engine.record_restatement` → `derived_metrics.restatement.recalc`.

---

# 8. Data contracts

`dcf_metrics.v1` · `forecast_metrics.v1` · `screening_metrics.v1` · `portfolio_metrics.v1` · `ask_agib_metrics.v1` · `api_metrics.v1`

Consumers use contracts rather than internal storage.

---

# 9. Mission Control / CLI / API

| Surface | Path / flag |
| --- | --- |
| Health | `GET /financial-statements/derived-metrics/health` · `--dme-health` |
| Dashboard | `…/dashboard` · `--dme-dashboard` |
| Calculate | `POST …/calculate/{ticker}` · `--dme-calculate TICKER` |
| Formulas | `…/formulas` · `--dme-formulas` |
| Contracts | `…/contracts/{id}/{ticker}` · `--dme-contract` |
| Lineage | `…/lineage/{metric}` · `--dme-lineage` |

---

# 10. Success criteria

* Exactly one canonical formula per derived metric
* Every metric versioned and traceable to validated facts
* Identical results for identical warehouse inputs
* Restatements trigger deterministic recalculation
* Mission Control exposes calculation health

---

**Acceptance:** DME importable; formulas registered centrally; calc from FWH only; immutable metric versions; contracts green; restatement recalc tested.
