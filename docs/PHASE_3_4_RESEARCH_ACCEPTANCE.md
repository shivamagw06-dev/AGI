# AGI Research Intelligence Acceptance Test v1.0

Permanent release gate **before** Research Intelligence is integrated into KUL.

## Targets

| Gate | Threshold |
|------|-----------|
| Questions | 400 |
| Passing score | ≥95% |
| Hallucinations | 0 |
| Recommendation leakage | 0 |
| Research memory leakage | 0 |
| Planner / module accuracy | 100% |
| Ask wired | `False` until Integration |

## Sections (A–K)

| Section | Theme | Count |
|---------|-------|------:|
| A | Annual Report Intelligence | 40 |
| B | Earnings Transcript Intelligence | 40 |
| C | Management Intelligence | 40 |
| D | Guidance Intelligence | 40 |
| E | Estimate Intelligence | 30 |
| F | Event Intelligence | 40 |
| G | Research Memory | 40 |
| H | Cross-Document Intelligence | 40 |
| I | Timeline Intelligence | 30 |
| J | Deep Research | 40 |
| K | Impossible Questions | 20 |
| **Total** | | **400** |

> Note: Cross-document and Deep Research are sized at 40 each so the suite totals exactly 400 while preserving coverage of all eleven themes.

## Scoring weights

| Component | Weight |
|-----------|-------:|
| Research Accuracy | 30% |
| Document Understanding | 20% |
| Cross-document Reasoning | 15% |
| Research Memory | 10% |
| Evidence Quality | 10% |
| Executive Communication | 10% |
| Uncertainty | 5% |

## Automatic fail conditions

Hallucination · Wrong company · Wrong document / quarter · Invented quote or guidance · Recommendation / price target · Framework leakage · Generic retrieval · Entity substitution · Timeline or memory corruption

## Permanent regression suites

After Acceptance, every release also runs:

1. **Research Golden 25** — fixed AR / transcripts / management / guidance / events / cross-doc set  
2. **Timeline Regression** — Q/FY chronology, leadership, acquisitions, guidance revisions  
3. **Research Memory Regression** — remember · update-not-duplicate · preserve history · no rewrite without evidence  

## Commands

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_research_intelligence_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_research_golden_25.py
PYTHONPATH=. python3 ask_product_test/run_research_timeline_regression.py
PYTHONPATH=. python3 ask_product_test/run_research_memory_regression.py
```

Artifacts: `/workspace/artifacts/research_intelligence_acceptance_v1.json` (and Golden / Timeline / Memory counterparts).

## Production release pipeline (post-integration)

```text
Production Regression
        ↓
Founder Evaluation
        ↓
Golden Founder 5
        ↓
Golden Business 20
        ↓
Financial Acceptance
        ↓
Business Acceptance
        ↓
Industry Acceptance
        ↓
Investment Acceptance
        ↓
Research Acceptance
        ↓
Research Golden 25
        ↓
Timeline Regression
        ↓
Research Memory Regression
        ↓
Coverage
        ↓
Concept
        ↓
Knowledge Unification
        ↓
Recommendation Policy
        ↓
Unknown Entity
        ↓
PASS
        ↓
Merge
```

Lifecycle: **Build → Acceptance → Integration → Production Validation → Freeze**.
