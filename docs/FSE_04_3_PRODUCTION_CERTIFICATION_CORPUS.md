# FSE-04.3 — Production Certification Corpus & Golden Dataset

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Specification — ready for implementation |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-04.3 |
| **Extends** | [FSE-04](FSE_04_PARSING_NORMALIZATION_ENGINE.md) · [FSE-04.1](FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md) · [FSE-04.2](FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md) |
| **Package** | `intelligence-engine/financial_statements_engine/parsing/pcc/` |
| **Corpus root** | `parsing/pcc/corpus/` |
| **Depends on** | FSE-01…FSE-04.2 |
| **Frozen surfaces** | Constitution · Governance Spec · Decision Engine · Gate · Eval Lab · IAT · MC contracts |

> **Intent:** Not a parser and not a validation engine. The Production Certification Corpus (PCC) is the permanent reference dataset against which every parser, schema, validation rule, replay engine, and FSE release is measured.

### Implementation pause recommendation

Implement **FSE-01 → FSE-04.3** before starting **FSE-05**. Validation must run against stable, benchmarked, continuously verified parse outputs. After FSE-04.3, the parsing subsystem is considered complete for Phase-1 purposes.

### Document series

| ID | Role |
| --- | --- |
| FSE-01…04 | Platform → evidence → schema → parse |
| FSE-04.1 | Parse Manifest / replay / certification framework |
| FSE-04.2 | Evidence Coverage Matrix / extraction audit |
| **FSE-04.3** | **Production Certification Corpus / Golden Dataset** |
| FSE-05 | [Validation & Financial Quality Engine](FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) |

---

# 1. Mission

Every production release of the Financial Statements Engine must prove correctness against a permanent Golden Dataset before deployment.

**No parser release may enter production without passing certification.**

The Certification Corpus is immutable, versioned, reproducible, and manually verified.

---

# 2. Architecture

```text
Raw Filing
      ↓
Expected Parse Manifest
      ↓
Expected Coverage Matrix
      ↓
Expected Canonical Draft
      ↓
Expected Validation Outcome   ← placeholder until FSE-05
      ↓
Certification Record
      ↓
Regression History
```

Runtime path for a release:

```text
Corpus Case → Parser → Manifest → Coverage Matrix → Canonical Draft
                ↓
         Comparison Engine vs Expected*
                ↓
         Certification Report → Pass/Fail → Deployment Recommendation
```

\* Expected artifacts are manually verified reference truth. Parser output never becomes reference truth automatically.

---

# 3. Design principles

| Principle | Rule |
| --- | --- |
| Read-only corpus | Certification never edits golden `expected/` |
| No production mutation | Certification never edits production warehouse data |
| No parser mutation | Certification never changes parser output |
| Compare only | Output is diffed against verified reference truth |
| Deterministic | Same corpus + same engine versions → same report |
| Version controlled | Corpus lives in git under `parsing/pcc/corpus/` |
| Reproducible | Every run is permanently stored under `results/` |

---

# 4. Corpus structure

```text
parsing/pcc/corpus/
    banking/
    nbfc/
    insurance/
    information_technology/
    manufacturing/
    automobile/
    pharma/
    fmcg/
    telecom/
    utilities/
    metals/
    oil_gas/
    infrastructure/
    healthcare/
    retail/
    chemicals/
    logistics/
    real_estate/
    mining/
    conglomerates/
```

Each company case:

```text
{sector}/{case_id}/
    metadata.json
    raw/
        filing.json          # or filing bytes + meta
    expected/
        metrics.json
        coverage.json
        manifest.json
        hierarchy.json
        unknown_labels.json
        validation.json      # FSE-05 placeholder
        lineage.json
        confidence.json
    results/                 # runtime only; never committed as truth
```

---

# 5. Expected artifacts

Every case holds (as applicable):

* Original Filing (`raw/`)
* Expected Parse Manifest fields
* Expected Coverage Matrix (core domain statuses + must-extract)
* Expected Canonical Metrics / Missing Metrics
* Expected Statement Hierarchy flags
* Expected Unknown Labels
* Expected Confidence floor
* Expected Lineage presence
* Expected Validation Result (deferred until FSE-05; recorded as `deferred`)
* Locked parser / schema / metric-registry version hints (informational)

---

# 6. Company metadata

`metadata.json` stores:

`company_id`, `company_name`, `sector`, `industry`, `exchange`, `reporting_standard`, `currency`, `statement_frequency`, `filing_type`, `financial_year`, `quarter`, `taxonomy_version`, `document_hash`, `ticker`, `case_id`, `verified_by`, `verified_at`, `immutable`

---

# 7. Sector coverage (initial)

Representative companies across Banks, NBFCs, Insurance, IT Services, Software, Manufacturing, Automobile, Steel, Cement, Power, Oil & Gas, Telecom, Healthcare, Pharmaceuticals, Retail, Consumer Goods, Infrastructure, Chemicals, Logistics, Real Estate, Mining — covering distinct reporting styles and accounting complexity.

Initial seed may be a **minimum viable golden set** (one case per priority sector) and grow without rewriting prior cases.

---

# 8. Certification execution

For every parser release:

1. Run parser on each corpus case
2. Generate Manifest, Coverage Matrix, Canonical Draft
3. Generate Validation Result (FSE-05; until then record `validation_status=deferred`)
4. Compare against reference truth
5. Generate Certification Report
6. Persist immutable certification record

**Only successful releases may proceed to deployment.**

---

# 9. Comparison engine

Compare:

* Parse Manifest (key fields / extracted metrics)
* Coverage Matrix (core domain statuses + must-extract)
* Statement Hierarchy
* Canonical Metrics (set + optional values)
* Unknown Labels
* Missing Metrics
* Confidence
* Validation Output (when FSE-05 active)
* Lineage presence

Every difference is recorded.

---

# 10. Regression detection

Automatically detect:

Lost Metrics · Additional Metrics · Changed Metric Values · Hierarchy Changes · Coverage Regression · Confidence Regression · Lineage Regression · Validation Regression · Schema Regression · Metric Registry Regression

Every regression identifies: Affected Companies · Affected Statements · Affected Metrics · Root Cause class.

---

# 11. Quality gates

| Gate | Threshold |
| --- | --- |
| Parse Manifest Match | 100% |
| Coverage Matrix Match | 100% |
| Hierarchy Preservation | 100% |
| Metric Mapping Accuracy | >99.5% |
| Unknown Label Rate | <0.5% |
| Validation Consistency | 100% (or deferred until FSE-05) |
| Replay Determinism | 100% |
| Regression Detection | 100% |
| Certification Pass | Required |

---

# 12. Certification report

Generate: Certification ID · Timestamp · Parser / Schema / Metric Registry versions · Companies Tested · Documents Processed · Metrics Compared · Coverage Score · Validation Score · Regression Summary · Pass/Fail · Deployment Recommendation.

---

# 13. Mission Control

Expose: Certification Dashboard · History · Parser Leaderboard · Coverage Leaderboard · Regression Trends · Sector Coverage · Golden Dataset Health · Failed Certifications · Pending Reviews · Historical Performance.

---

# 14. Engineering principles

* Golden Dataset is immutable
* Reference truth is manually verified
* Parser output never becomes reference truth automatically
* Candidate freezes write to `results/candidates/` only
* Every certification run is permanently stored; history is never deleted

---

# 15. Events

| Event | When |
| --- | --- |
| `pcc.certification.started.v1` | Corpus run begins |
| `pcc.certification.completed.v1` | Corpus run finishes (pass or fail) |
| `pcc.certification.failed.v1` | Corpus run fails gates |
| `pcc.case.failed.v1` | Single case mismatch |
| `pcc.regression.detected.v1` | Regression vs prior certification |

---

# 16. Success criteria

* Every production parser release is certified before deployment
* Every regression is automatically detected
* Every certification run is reproducible
* Mission Control exposes complete certification history
* No parser, schema, replay engine, or validation engine may enter production without passing the PCC

---

**Acceptance:** FSE-04.3 importable; corpus loadable by sector; certification run produces immutable report; gates enforced; MC dashboard green; tests cover compare/regress/certify paths.
