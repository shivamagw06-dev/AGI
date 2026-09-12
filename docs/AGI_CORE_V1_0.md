# AGI Core v1.0

**Status:** Frozen  
**Regression:** Production Release Gate  
**Owner:** Core Platform  
**Baseline date:** 2026-08-02  

AGI Core v1.0 is the versioned behavioral baseline for the institutional Ask
platform after Phase 3.0 Business Intelligence integration and production
validation. Future work must improve the platform **without changing these
components' expected behavior**, unless there is a deliberate version bump
(e.g. AGI Core v1.1).

Machine-readable twin: `intelligence-engine/ask_product_test/agi_core_v1_0.py`

---

## Frozen components

| Component | Module / surface | Acceptance |
|---|---|---|
| Financial Foundations | `financial_foundations` | Accounting / journal / three-statement linkage via Financial Router + AFI |
| Financial Intelligence | `financial_statement_intelligence` + Financial Router | AFI ≥95%, routing 100%, pollution 0 |
| Financial Concepts | `financial_concepts` | Concept Acceptance 100% + AFI concept section |
| Business Intelligence | `business_intelligence.foundation` | BI Acceptance 100%, Business Integration 100%, Golden Business 20 |
| Knowledge Unification | `knowledge_unification` | KUL Acceptance 100%; sole Ask soft-wire for BI/FF/FSI/Concepts |
| Coverage Intelligence | CapIQ IKT + coverage / unknown-entity policy | Coverage Acceptance (PR-scoped PASS), Unknown Entity PASS |

Supporting permanent product policies (also gated):

- Recommendation Policy — no buy/sell/target-price
- Unknown Entity — refuse, never invent
- Executive answer-first — no framework leakage

---

## Freeze rule

Within AGI Core v1.0:

**Allowed**
- Bug fixes that restore baseline behavior
- Performance / latency improvements that do not change answers
- Coverage expansion (more companies) that does not weaken refusal policy
- Documentation and observability
- New capabilities **outside** these components (e.g. Industry Intelligence as a later phase) that do not regress the gate

**Not allowed without a deliberate Core version update**
- Changing expected answers or scoring targets of the release suites below
- Weakening recommendation / unknown-entity / coverage refusal policy
- Bypassing Knowledge Unification for Core financial/business short-circuits
- Dropping or relaxing Production Release Gate suites

---

## Production Release Gate (permanent)

Every future PR **must** run the Production Release Gate and **PASS** before merge:

```text
Production Regression
        │
        ▼
Founder Evaluation V2 → Golden Founder 5 → Golden Business 20
        │
        ▼
Financial Intelligence Acceptance (AFI)
        │
        ▼
Business Intelligence + Integration
        │
        ▼
Industry Acceptance + Integration → Founder Evaluation V3
        │
        ▼
Coverage → Concept → KUL → Recommendation Policy → Unknown Entity
        │
        ▼
Canonical Classification → Company Metadata Routing
        │
        ▼
Core Platform Acceptance → Answer Quality
        │
        ▼
      PASS → Merge
```

Frozen Core v1.0 components are unchanged. Suites below the Core block
(industry / founder v3 / identity / platform / answer quality) were absorbed
from `main` so the permanent gate does not drop production coverage.

### Targets

| Suite | Target |
|---|---|
| Founder Evaluation V2 | ≥95% |
| Golden Founder 5 | 5/5 |
| Golden Business 20 | 20/20 |
| Financial Intelligence (AFI) | ≥95% overall; routing 100%; pollution 0; hallucinations 0 |
| Business Intelligence Acceptance | 100% |
| Business Integration | 100% |
| Industry Acceptance | 100% |
| Industry Integration | 100% |
| Founder Evaluation V3 | ≥95% |
| Coverage Acceptance | PR-scoped PASS |
| Concept Acceptance | 100% |
| Knowledge Unification | 100% |
| Recommendation Policy | PASS |
| Unknown Entity | PASS |
| Canonical Classification | 100% |
| Company Metadata Routing | 100% |
| Core Platform Acceptance | ≥98% + zero-defect |
| Answer Quality | ≥95% |
| Hallucinations | 0 |

### How to run

```bash
cd intelligence-engine
ASK_TEST_MODE=inprocess python3 -m ask_product_test.run_production_regression_v1
```

CI workflow: `.github/workflows/production-regression.yml`  
Local quick iteration (not merge-sufficient): `PROD_REGRESSION_QUICK=1`

---

## Baseline evidence (inprocess, 2026-08-02)

| Gate | Result |
|---|---|
| BI Acceptance | 100% |
| Business Integration | 100% |
| Golden Business 20 | 20/20 |
| Golden Founder 5 | 5/5 |
| Founder Evaluation V2 | 100% (50/50) |
| KUL | 100% (60/60) |
| Concept | 100% (12/12) |
| Recommendation Policy | PASS |
| Unknown Entity | PASS |
| Coverage | PR-scoped PASS |
| AFI | 96.42% |
| Full Production Regression | **PASS** · `phase3_freeze_ready=True` |

---

## Version updates

| Version | When |
|---|---|
| **v1.0** | Phase 3.0 BI + production validation frozen (this document) |
| v1.1 | Deliberate Core behavior change with updated suites + release notes |
| v2.0 | Reserved for intentional architectural evolution of Core |

Industry Intelligence and later phases build **on** AGI Core v1.0 — they do not
rewrite these components' contracts without a Core version bump.
