# Phase 3.0.5 — Business Intelligence Integration

## Objective

Wire the Phase 3.0 BI Foundation into Ask **through KUL**, the same lifecycle
pattern as Financial Foundations → Phase 2.5 integration. Engine acceptance
(100/100) is necessary but not sufficient; product validation requires KUL
routing + live integration suite + founder/regression gates.

## What changed

1. **KUL provider** `business_intelligence` wraps `foundation.analyse`
2. **Query planner** detects business / moat / unit-economics / comparison /
   business-risk / growth intents deterministically
3. **Knowledge planner** uses a BI-first menu (BI → CapIQ → memory → IKL → KF →
   CGL → legacy) for business-shaped questions; industry pedagogy without a
   ticker uses BI → KF → concepts (no generic retrieval default)
4. **Fusion** prefers BI summaries for business-typed questions
5. **Hard provider** — BI can short-circuit Ask via `answer_for_ask` (still
   after coverage / recommendation / unknown-entity policies in `UiService`)
6. Foundation `ask_wired: true` via `knowledge_unification.providers.business_intelligence`

## What did **not** change

- No parallel Ask short-circuit bypassing KUL
- Recommendation policy, coverage policy, executive composer unchanged
- CapIQ pedagogy false-bind guards preserved
- Industry Intelligence remains a later phase

## Acceptance

```bash
cd intelligence-engine
python3 -m ask_product_test.run_bi_integration_acceptance_v1
```

~28 questions · gate ≥90% · `/workspace/artifacts/bi_integration_acceptance_v1.json`

Assertions: BI selected, KUL plan includes BI, not legacy-only, direct answer
first, no hallucination / false CapIQ binds, evidence fusion when company-bound.

## Production validation status (inprocess)

| Gate | Result |
|---|---|
| BI Acceptance | ✅ 100/100 |
| Business Integration | ✅ 28/28 |
| Golden Business 20 | ✅ 20/20 |
| Golden Founder 5 | ✅ 5/5 |
| Founder Evaluation V2 | ✅ 50/50 (100%) |
| KUL | ✅ 60/60 |
| Concept | ✅ 12/12 |
| Recommendation Policy | ✅ PASS |
| Unknown Entity | ✅ PASS |
| Coverage | ✅ PR-scoped PASS (known pre-existing NSE twins remain) |
| AFI overall | ✅ 96.42% (routing/engine util 100%, pollution 0, hallucinations 0) |

AFI quality fixes that cleared the freeze bar:
- Answer scoring no longer triple-counts mirrored SearchView fields
- Ambiguous causal events (`PAT doubled. What happened?`) clarify company/period
- Named BI pedagogy for Ferrari/Toyota/Reliance (luxury vs mass; O2C/Jio/Retail)
- Company-less moat concepts lead with `financial_concepts`
- KUL fusion trims soft-provider why pollution; topic matching normalizes hyphens

```bash
cd intelligence-engine
ASK_TEST_MODE=inprocess python3 -m ask_product_test.run_production_regression_v1 --with-afi
```

**Phase 3.0 is frozen into AGI Core v1.0.** See `docs/AGI_CORE_V1_0.md`.

Permanent merge policy: every future PR must PASS the Production Release Gate
(`.github/workflows/production-regression.yml`). Industry Intelligence and later
phases build on this baseline; they must not change Core expected behavior
without a deliberate Core version bump.
See `ask_product_test/PRODUCTION_REGRESSION_V1.md`.
