# FSE-03 — Canonical Financial Data Model & Schema

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-03 |
| **Depends on** | [FSE-01](FSE_01_FINANCIAL_STATEMENTS_ENGINE.md), [FSE-02](FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md) |
| **Package** | `intelligence-engine/financial_statements_engine/cfdm/` |
| **Metric Registry** | `intelligence-engine/financial_statements_engine/metric_registry/` |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine formulas · Institutional Gate · Evaluation Lab · IAT · Mission Control contracts |

> **Criticality:** Once this schema is wrong, everything built on top becomes painful to change. Treat metric identity, statement scope, units, and versioning as frozen contracts after M0.

### Document series

| ID | Document | Role |
| --- | --- | --- |
| FSE-01 | Architecture & Principles | What the architecture is |
| FSE-02 | Data Sources & Collection Pipeline | How data enters |
| **FSE-03** | **Canonical Financial Data Model & Schema** | **Authoritative financial representation** |
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

The Canonical Financial Data Model (CFDM) defines the single, authoritative representation of all financial information within AGIB.

It provides a normalized, versioned, and extensible schema that ensures every downstream consumer interprets financial data consistently.

The CFDM is the foundation for:

* Valuation
* Screening
* Forecasting
* Company Memory
* Ask AGIB
* Portfolio Analytics
* Risk Analysis
* Research Reports
* APIs

**No downstream system shall define its own financial schema.**

---

# 2. Design Principles

The schema shall be:

* Canonical
* Normalized
* Extensible
* Immutable
* Versioned
* Auditable
* Source-aware
* Currency-aware
* Unit-aware
* Reporting-standard agnostic

---

# 3. Architecture

```text
Raw Evidence
      ↓
Parsed Statement
      ↓
Canonical Statement
      ↓
Financial Facts
      ↓
Derived Metrics
      ↓
Consumers
```

Only the **Canonical Statement** and **Financial Facts** (plus separately stored **Derived Metrics**) are exposed to consumers.

Parsed / extractor-local shapes are internal to FSE-04 and must not leak to consumers.

---

# 4. Canonical Objects

The Financial Warehouse consists of the following logical objects:

```text
Company
Reporting Period
Statement
Financial Fact
Derived Metric
Validation Result
Version
Evidence Reference
```

Each object has a single responsibility.

### Package mapping

| Object | Module |
| --- | --- |
| Company | `cfdm/company.py` |
| Reporting Period | `cfdm/period.py` |
| Statement | `cfdm/statement.py` |
| Financial Fact | `cfdm/fact.py` |
| Derived Metric | `cfdm/derived_metric.py` |
| Validation Result | `cfdm/validation_result.py` |
| Version | `cfdm/version_record.py` |
| Evidence Reference | `cfdm/evidence_ref.py` |
| Object contracts / enums | `cfdm/schema.py` |
| Builders / identity helpers | `cfdm/models.py` |
| Metric Registry service | `metric_registry/` (see §22) |

---

# 5. Company

Every company shall have one canonical record.

### Mandatory fields

| Field | Type | Notes |
| --- | --- | --- |
| `company_id` | string | Stable AGIB id (prefer ISIN when known; else `EXCHANGE:TICKER`) |
| `exchange` | string | e.g. `NSE`, `BSE` |
| `ticker` | string | Exchange symbol |
| `isin` | string \| null | |
| `legal_name` | string \| null | |
| `sector` | string \| null | |
| `industry` | string \| null | |
| `currency` | string | ISO-like reporting currency, default `INR` |
| `reporting_standard` | string | e..g. `IND_AS`, `IFRS`, `US_GAAP` |
| `fiscal_year_end` | string | `MM-DD` (e.g. `03-31`) |
| `status` | string | `active` \| `suspended` \| `delisted` |

---

# 6. Reporting Period

Every statement belongs to exactly one reporting period.

| Field | Type | Notes |
| --- | --- | --- |
| `period_id` | string | Deterministic: `{company_id}:{period_end}:{period_kind}:{scope}` |
| `company_id` | string | |
| `statement_date` | date \| null | As-of / board approval date when known |
| `filing_date` | date \| null | Exchange filing date |
| `period_start` | date \| null | |
| `period_end` | date | Required |
| `fiscal_year` | int \| null | |
| `quarter` | string \| null | `Q1`…`Q4`, `H1`, `H2`, `9M`, `FY` |
| `period_kind` | string | `annual` \| `quarterly` \| `half_year` \| `nine_months` \| `other` |
| `statement_scope` | string | See §13 |
| `consolidation_type` | string | `standalone` \| `consolidated` \| `unknown` |

Examples: `FY2025`, `Q1 FY2026`, `H1`, `Nine Months`, Annual / Standalone / Consolidated.

**Never merge standalone and consolidated into one period identity.**

---

# 7. Statement

Each reporting period contains multiple statements.

Supported `statement_type` values:

| Type | Code |
| --- | --- |
| Income Statement | `income_statement` |
| Balance Sheet | `balance_sheet` |
| Cash Flow | `cash_flow` |
| Segment Statement | `segment_statement` |
| Notes | `notes` |
| Share Capital | `share_capital` |
| EPS | `eps` |

Statements are immutable once published. Identity:

```text
statement_id = {period_id}:{statement_type}:v{version}
```

---

# 8. Financial Fact

This is the core entity. Each row represents exactly one financial fact.

| Field | Type | Notes |
| --- | --- | --- |
| `fact_id` | string | Deterministic hash of identity + version |
| `company_id` | string | |
| `period_id` | string | |
| `statement_type` | string | |
| `metric` | string | **Canonical only** (Metric Registry) |
| `reported_value` | number \| null | As reported |
| `normalized_value` | number \| null | Absolute currency units (ones) |
| `currency` | string | |
| `unit` | string | Display unit label |
| `scale` | string | `ones` \| `thousands` \| `lakhs` \| `crores` \| `millions` \| `billions` |
| `source` | string | Source code (FSE-02) |
| `confidence` | number | 0–1 |
| `version` | int | |
| `status` | string | `draft` \| `published` \| `withheld` \| `flagged` \| `superseded` |
| `created_at` | datetime | |
| `updated_at` | datetime | Metadata only; value immutability still holds |

### Example

| Company | Period | Statement | Metric | Value |
| --- | --- | --- | --- | ---: |
| RELIANCE | FY2025 | Income | revenue | 267000 |
| RELIANCE | FY2025 | Balance | cash | 194000 |
| RELIANCE | FY2025 | CashFlow | operating_cash_flow | 39100 |

### Fact identity (excluding version)

```text
(company_id, period_id, statement_type, metric, consolidation_type)
```

Same identity + different normalized content ⇒ new `version` (never in-place edit).

---

# 9. Metric Dictionary

Every metric has one canonical identifier.

Examples:

```text
revenue
net_income
ebit
ebitda
cash
inventory
receivables
current_assets
current_liabilities
operating_cash_flow
free_cash_flow
```

**No synonyms exist inside the warehouse.** Warehouse rows always store the canonical `metric` string.

---

# 10. Synonym Registry

Incoming names are mapped to canonical metrics **before** fact materialization.

Examples:

```text
Revenue / Revenue From Operations / Sales / Net Sales  →  revenue
PAT / Net Profit / Profit After Tax / pat               →  net_income
```

The synonym registry is centrally maintained and **versioned** inside the Metric Registry service (§22).

Parsers, validators, and consumers must not maintain private synonym tables.

---

# 11. Units

Every financial fact records:

```text
currency
unit
scale
```

Examples: `INR`, Millions, Crores, Thousands, Absolute (`ones`).

**Consumers never infer units.** If `scale` or `currency` is unknown, `normalized_value` must be null and status must not be silently published as absolute truth without a validation flag.

Scale conversion constants live only in Metric Registry / CFDM helpers.

---

# 12. Source Attribution

Every fact links back to evidence via `Evidence Reference`:

| Field | Notes |
| --- | --- |
| `evidence_id` | FSE-01/02 raw evidence id |
| `source` | Source code |
| `source_document` | URL or blob path |
| `page` | optional |
| `section` | optional |
| `line_reference` | optional |
| `parser_version` | FSE-04 |
| `collector_version` | FSE-02 |
| `confidence` | 0–1 |

Every number must be explainable. Facts without `evidence_id` cannot reach `published` (aligns with FSE-01 `TRACE_EVIDENCE`).

---

# 13. Statement Scope

Support:

```text
standalone
consolidated
restated
revised
```

Encoding:

* `consolidation_type` ∈ {`standalone`, `consolidated`, `unknown`}
* `statement_scope` ∈ {`as_reported`, `restated`, `revised`}

**Never merge standalone and consolidated statements.**

---

# 14. Versioning

Every financial fact / statement contains:

```text
version
previous_version
change_reason
effective_date
```

Historical versions are immutable. Restatement detection (FSE-02/FSE-06) creates new versions; it never mutates prior rows.

---

# 15. Validation Status

Every fact (and statement aggregate) stores:

```text
validation_status
validation_score
validation_timestamp
validation_engine_version
```

Consumers can filter by validation quality. Validation engines (FSE-05) write `Validation Result` objects; they never edit fact values.

---

# 16. Derived Metrics

Derived metrics are stored separately from reported facts.

| Field | Notes |
| --- | --- |
| `metric` | Canonical derived metric id |
| `formula` | Registry formula id / expression |
| `dependencies` | List of canonical metric ids |
| `calculated_value` | number \| null |
| `calculation_version` | string |
| `calculation_timestamp` | datetime |
| `period_id` / `company_id` | linkage |

**Derived metrics never overwrite reported facts.**

---

# 17. Metric Categories

Canonical metrics are grouped into domains (authoritative list in Metric Registry + Appendix A).

### Income Statement
Revenue · Other Income · EBITDA · EBIT · Finance Cost · Tax · Net Income · EPS …

### Balance Sheet
Cash · Inventory · Receivables · Investments · Assets · Liabilities · Equity …

### Cash Flow
Operating · Investing · Financing · Free Cash Flow · Net Cash Change …

### Segment Reporting
Segment Revenue · Segment Profit · Segment Assets …

### Capital Structure
Share Capital · Treasury Shares · Minority Interest …

---

# 18. Immutability Rules

* Published facts cannot be edited.
* Updates create new versions.
* Previous versions remain accessible forever.
* Raw evidence remains immutable (FSE-01/02).

---

# 19. Consumer Rules

Consumers are read-only.

Consumers cannot:

* modify facts
* rename metrics
* calculate replacements that overwrite warehouse values
* maintain parallel financial schemas

All calculations that become platform truth must be registered as Derived Metrics and written by FSE derived engines — not ad hoc in Ask/Valuation modules.

---

# 20. Extensibility

New metrics must be added through the **Metric Registry** (version bump), not by forking consumer schemas.

No relational schema migration should be required for adding additional financial metrics when facts are stored as metric-keyed documents / wide-evolving fact tables.

Deprecation:

* Metrics may be marked `deprecated` with `replaced_by`
* Deprecated metrics remain readable for history
* New publishes must use the replacement canonical id

---

# 21. Success Criteria

The Canonical Financial Data Model is considered complete when:

* Every financial concept has a unique canonical identifier.
* Every fact is traceable to evidence.
* Every reporting period is immutable in identity.
* Every revision creates a new version.
* Every consumer reads the same normalized representation.
* New financial metrics can be introduced without redesigning the schema.
* Parsers / validators / consumers all query the Metric Registry (no private copies).

---

# 22. Architectural Improvement — Metric Registry Service

FSE-03 introduces a **Metric Registry** as its own versioned service (not scattered constants).

### Responsibility

Define and serve:

* Canonical metric name
* Description
* Synonyms
* Statement type / category
* Unit rules (allowed scales, default scale)
* Validation rule hooks (ids for FSE-05)
* Calculation dependencies (if derived)
* Deprecation status / replacement

### Topology

```text
Metric Registry (versioned)
        ↑
   ┌────┼──────────────┐
   │    │              │
Parser Validator  Consumers
(FSE-04) (FSE-05) (FSE-09, CM, Ask, …)
```

### Module layout

```text
financial_statements_engine/metric_registry/
  __init__.py
  schema.py           # registry version, metric record contract
  dictionary.py       # seeded canonical metrics (Appendix A + extensions)
  synonyms.py         # synonym → canonical map (versioned)
  service.py          # resolve / get / list / validate_metric_name
  production.py       # health / manifest façades
```

### Compatibility

`financial_statements_engine/registry.py` becomes a **thin façade** over Metric Registry so existing FSE-01 code keeps working without maintaining a second dictionary.

### Registry versioning

| Field | Example |
| --- | --- |
| `registry_version` | `cfdm-metric-registry-v1.0.0` |
| `workstream_id` | `FSE-03` |

Any synonym or canonical add/rename/deprecate requires a registry version bump and changelog entry in `metric_registry/CHANGELOG.md`.

---

# 23. JSON Shapes (normative)

### Financial Fact

```json
{
  "fact_id": "…",
  "company_id": "INE002A01018",
  "period_id": "INE002A01018:2025-03-31:annual:consolidated",
  "statement_type": "income_statement",
  "metric": "revenue",
  "reported_value": 267000.0,
  "normalized_value": 2670000000000.0,
  "currency": "INR",
  "unit": "crores",
  "scale": "crores",
  "source": "nse_xbrl",
  "confidence": 0.95,
  "version": 1,
  "previous_version": null,
  "change_reason": null,
  "effective_date": "2025-05-01",
  "status": "published",
  "validation_status": "passed",
  "validation_score": 1.0,
  "validation_timestamp": "2026-07-29T00:00:00+00:00",
  "validation_engine_version": "fse-05-pending",
  "evidence": {
    "evidence_id": "sha256:…",
    "source": "nse_xbrl",
    "source_document": "https://…",
    "parser_version": "nse_indas_xbrl_v1",
    "collector_version": "fse-02-v1.0.0",
    "confidence": 0.95
  },
  "created_at": "2026-07-29T00:00:00+00:00",
  "updated_at": "2026-07-29T00:00:00+00:00"
}
```

---

# 24. Public Interfaces

## CLI

```bash
python -m financial_statements_engine --cfdm-health
python -m financial_statements_engine --metric-registry
python -m financial_statements_engine --resolve-metric "Revenue From Operations"
python -m financial_statements_engine --resolve-metric pat
```

## HTTP

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/financial-statements/cfdm/health` | CFDM + registry health |
| GET | `/v1/financial-statements/metrics` | List canonical metrics |
| GET | `/v1/financial-statements/metrics/{metric}` | Metric record |
| GET | `/v1/financial-statements/metrics/resolve` | `?name=` synonym resolve |

## Python

```python
from financial_statements_engine.metric_registry import resolve, get_metric, list_metrics
from financial_statements_engine.cfdm import build_fact, build_period, build_company
```

---

# 25. Alignment with prior FSE packages

| Prior name (FSE-01 scaffold) | FSE-03 canonical |
| --- | --- |
| `pat` | `net_income` |
| `pbt` | `profit_before_tax` |
| `finance_costs` | `finance_cost` |
| `employee_benefit_expense` | `employee_cost` |
| `equity_share_capital` | `share_capital` |
| `net_change_in_cash` | `net_cash_change` |
| `expenses` | prefer `operating_expenses` / `cogs` when known |
| `revenue_from_operations` (P2.1) | `revenue` |

Legacy keys remain **synonyms only**. New publishes must use FSE-03 canonical ids.

---

# 26. Test Requirements

1. Every Appendix A metric exists exactly once in the registry
2. Synonym `Revenue From Operations` → `revenue`
3. Synonym `PAT` / `pat` → `net_income`
4. Warehouse reject helper: non-canonical metric name fails `assert_canonical`
5. `build_fact` requires `evidence_id` for `status=published`
6. Standalone vs consolidated periods produce different `period_id`
7. Registry version present in health payload
8. `registry.py` façade resolves identically to Metric Registry service
9. No BUY/SELL / recommendation fields in CFDM public payloads

---

# 27. Non-Goals (v1)

* Full IND-AS notes taxonomy
* Global multi-GAAP presentation overlays (structure must allow later)
* LLM-inferred metrics without evidence
* Consumer-local metric aliases

---

# 28. Implementation Checklist

- [ ] `cfdm/schema.py` + object builders
- [ ] `metric_registry/` service with Appendix A seed + synonyms
- [ ] Façade `registry.py` → Metric Registry
- [ ] CLI + HTTP surfaces
- [ ] Series links in FSE-01/02
- [ ] Tests in §26

**Acceptance for this PR:** FSE-03 spec committed; Metric Registry is single naming authority; CFDM builders enforce evidence + canonical metrics; tests green.

---

# Appendix A — Core Financial Metric Dictionary (Initial)

| Category | Canonical Metric |
| --- | --- |
| Income | `revenue` |
| Income | `other_income` |
| Income | `total_income` |
| Income | `cogs` |
| Income | `employee_cost` |
| Income | `operating_expenses` |
| Income | `ebitda` |
| Income | `depreciation` |
| Income | `ebit` |
| Income | `finance_cost` |
| Income | `profit_before_tax` |
| Income | `tax_expense` |
| Income | `net_income` |
| Income | `eps_basic` |
| Income | `eps_diluted` |
| Balance | `cash` |
| Balance | `receivables` |
| Balance | `inventory` |
| Balance | `current_assets` |
| Balance | `total_assets` |
| Balance | `current_liabilities` |
| Balance | `total_liabilities` |
| Balance | `share_capital` |
| Balance | `retained_earnings` |
| Balance | `total_equity` |
| Cash Flow | `operating_cash_flow` |
| Cash Flow | `investing_cash_flow` |
| Cash Flow | `financing_cash_flow` |
| Cash Flow | `free_cash_flow` |
| Cash Flow | `net_cash_change` |

Extended (registry v1, non-appendix but required for India equity continuity):

`non_current_assets`, `non_current_liabilities`, `total_debt`, `working_capital`, `equity_owners`, `reserves`, `face_value`, `shares_outstanding`, `deposits`, `capex`, `pat_owners`, `investments`, `minority_interest`, `treasury_shares`, `segment_revenue`, `segment_profit`, `segment_assets`
