# FSE-04.2 — Evidence Coverage Matrix & Extraction Audit

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-04.2 |
| **Extends** | [FSE-04](FSE_04_PARSING_NORMALIZATION_ENGINE.md) · [FSE-04.1](FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md) |
| **Package** | `intelligence-engine/financial_statements_engine/parsing/coverage/` |
| **Depends on** | FSE-01…FSE-04.1 |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** Not a new parser and not validation. This is the extraction audit layer that makes every parsed document measurable, auditable, explainable, and operationally observable before FSE-05 begins.

### Implementation pause recommendation

Implement **FSE-01 → FSE-04.3** before starting **FSE-05**. Validation must be able to distinguish *missing cash flow in the filing* from *parser failed to extract cash flow*. The Coverage Matrix creates that separation; the Production Certification Corpus locks it as ground truth.

### Document series

| ID | Role |
| --- | --- |
| FSE-01…04 | Platform → evidence → schema → parse |
| FSE-04.1 | Parse Manifest / replay / certification |
| **FSE-04.2** | **Evidence Coverage Matrix / extraction audit** |
| FSE-04.3 | [Production Certification Corpus](FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md) — golden dataset |
| FSE-05 | [Validation & Financial Quality Engine](FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) |

---

# 1. Mission

Every parsed document shall produce an immutable **Evidence Coverage Matrix**.

The matrix answers:

* What information exists in this filing?
* What information was successfully extracted?
* What information is missing?
* What information is unsupported by the parser?
* What information requires engineering attention?

The Coverage Matrix is an **extraction audit**. It is **not** validation.

---

# 2. Architecture

```text
Raw Evidence
      ↓
Parser (FSE-04)
      ↓
Parse Manifest (FSE-04.1)
      ↓
Evidence Coverage Matrix (FSE-04.2)   ← observational audit
      ↓
Canonical Draft
      ↓
Validation Engine (FSE-05)
      ↓
Financial Warehouse
```

Coverage is generated **after** parsing and Parse Manifest creation, and **before** validation consumes the draft.

---

# 3. Design principles

| Principle | Rule |
| --- | --- |
| Coverage measures extraction | Never measures accounting correctness |
| Observational only | Never modifies financial data |
| No accounting | Never calculates accounting relationships |
| No invention | Never guesses missing information |
| Deterministic | Same inputs → same matrix |
| Immutable | Matrices are never overwritten |
| Traceable | Linked to `manifest_id`, `draft_id`, `document_hash`, parser versions |

---

# 4. Evidence categories (domains)

Every document is evaluated against these domains. Each receives exactly one extraction status.

| Domain key | Display name |
| --- | --- |
| `income_statement` | Income Statement |
| `balance_sheet` | Balance Sheet |
| `cash_flow` | Cash Flow Statement |
| `equity_changes` | Statement of Changes in Equity |
| `quarterly_results` | Quarterly Results |
| `annual_results` | Annual Results |
| `segment_reporting` | Segment Reporting |
| `share_capital` | Share Capital |
| `eps` | EPS |
| `dividend` | Dividend Information |
| `debt_schedule` | Debt Schedule |
| `lease_liabilities` | Lease Liabilities |
| `deferred_tax` | Deferred Tax |
| `working_capital` | Working Capital |
| `related_party` | Related Party Transactions |
| `auditor` | Auditor Information |
| `mda` | Management Discussion |
| `corporate_info` | Corporate Information |
| `notes` | Notes to Accounts |
| `accounting_policies` | Accounting Policies |
| `contingent_liabilities` | Contingent Liabilities |
| `capital_commitments` | Capital Commitments |
| `subsidiaries` | Subsidiaries |
| `joint_ventures` | Joint Ventures |
| `associates` | Associates |
| `financial_instruments` | Financial Instruments |
| `oci` | Other Comprehensive Income |

---

# 5. Extraction status

Exactly one of:

| Status | Meaning |
| --- | --- |
| `FOUND` | All expected information extracted |
| `PARTIAL` | Some information extracted |
| `MISSING` | Expected but not found |
| `NOT_PRESENT` | Company did not report the section |
| `UNSUPPORTED` | Parser does not currently support this section |
| `PARSE_FAILED` | Section exists but extraction failed |

---

# 6. Section metrics

Every section records:

* `section_name`
* `status`
* `expected_metrics`
* `extracted_metrics`
* `missing_metrics`
* `unknown_labels`
* `confidence`
* `page_numbers`
* `table_count`
* `row_count`
* `parser_version`
* `processing_time_ms`

---

# 7. Document scorecard

Informational only — **never blocks publication**.

* Coverage Percentage
* Unknown Label Count
* Unsupported Sections
* Parser Confidence
* Extraction Completeness
* Document Completeness
* Section Count
* Processing Time

---

# 8. Missing metric report

Structured rows: Metric · Expected · Extracted · Reason · Status · Action.

Examples:

| Metric | Status | Action |
| --- | --- | --- |
| Revenue | Missing | Investigate parser |
| Segment Revenue | Unsupported | Add parser capability |
| EPS Diluted | Not Present | No action |

---

# 9. Unknown label report

Unknown labels enter the Unknown Metric Review Queue (FSE-04.1). Coverage stores an audit projection:

* `original_label`, `page`, `section`, `document`, `candidate_metric`, `confidence`, `review_status`

Nothing is discarded.

---

# 10. Coverage history

Every document maintains historical coverage. Coverage changes between parser versions are permanent.

```text
Parser v1 → 82%
Parser v2 → 96%
Diff      → +14%
```

---

# 11. Coverage difference engine

Compare old vs new coverage matrices:

* New Sections / Lost Sections
* Coverage Gain / Coverage Loss
* Unknown Labels Resolved / Introduced

Used in parser certification.

---

# 12. Mission Control surfaces

* Overall Coverage
* Coverage by Parser / Company / Filing / Industry / Statement Type
* Unsupported Sections
* Unknown Label Queue
* Coverage Trends
* Coverage Improvements
* Coverage Regression Alerts

---

# 13. Quality targets

| Target | Threshold |
| --- | --- |
| Income Statement Coverage | >99% |
| Balance Sheet Coverage | >99% |
| Cash Flow Coverage | >99% |
| Unknown Label Rate | <0.5% |
| Unsupported Section Rate | <2% |
| Coverage Determinism | 100% |
| Coverage Traceability | 100% |
| Coverage History | 100% |

Targets are operational KPIs. Scorecards do not gate warehouse writes (FSE-05 owns publication gates).

---

# 14. Engineering principles

* Coverage is observational
* Coverage never edits data
* Coverage never validates accounting
* Coverage never modifies canonical drafts
* Coverage is generated for every successfully parsed document
* Coverage is immutable, reproducible, fully traceable

---

# 15. Events

| Event | When |
| --- | --- |
| `coverage.matrix.created.v1` | Matrix persisted |
| `coverage.regression.detected.v1` | Diff shows material coverage loss |
| `coverage.history.appended.v1` | History entry recorded |

---

# 16. Success criteria

* Every parsed document produces an Evidence Coverage Matrix
* Every evidence section has an explicit extraction status
* Every missing metric is reported
* Every unknown label is queued for review
* Mission Control exposes coverage analytics
* Coverage regressions are detected between parser releases
* The Coverage Matrix is the operational audit layer for AGIB parsing before FSE-05

---

**Acceptance:** FSE-04.2 importable; every successful parse emits an immutable coverage matrix; scorecard/missing/unknown/history/diff/MC analytics tests green; scorecard never blocks publication.
