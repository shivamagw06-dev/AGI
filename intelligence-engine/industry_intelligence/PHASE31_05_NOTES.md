# Phase 3.1.5 — Industry Intelligence Integration

## Objective

Wire Industry Intelligence into Ask **through KUL**, same pattern as Phase 3.0.5 BI integration.

Engine acceptance (200/200) was necessary but not sufficient. This phase proves live provider selection, Industry DNA usage, and BI consumption of DNA.

## What changed

1. **KUL provider** `industry_intelligence` wraps `industry_intelligence.production.analyse`
2. **Query planner** detects industry / KPI / valuation / cycle / competition intents
3. **Knowledge planner** menus:
   - Pure industry pedagogy → II → BI → KF → concepts
   - Company business → BI → II (DNA enrich) → CapIQ → memory → KF
4. **Fusion** leads with Industry DNA for company-less industry questions; BI leads company business questions
5. **BI consumes Industry DNA** via `industry_drivers.template_for` overlay (Porter, value drivers, capital intensity, risks, valuation methods)
6. `ASK_WIRED = True` via `knowledge_unification.providers.industry_intelligence`
7. **Knowledge Dependency Map** — `docs/KNOWLEDGE_DEPENDENCY_MAP.md`

## What did **not** change

- No parallel Ask short-circuit bypassing KUL
- AGI Core v1.0 modules untouched
- CapIQ false-bind guards preserved (real-estate pedagogy no longer binds a random CapIQ name)

## Acceptance

```bash
cd intelligence-engine
python3 ask_product_test/run_industry_intelligence_acceptance_v1.py   # 200/200
python3 ask_product_test/run_ii_integration_acceptance_v1.py         # 48/48
python3 ask_product_test/run_founder_evaluation_v3.py                # ≥95%
```

## Freeze gate (Phase 3.1)

| Test | Target |
|------|--------|
| Industry Acceptance | 200/200 |
| Industry Integration | 100% |
| Founder Evaluation V3 | ≥95% |
| Golden Founder 5 | PASS |
| Golden Business 20 | PASS |
| AFI | PASS |
| Coverage / Concept / KUL / Reco / Unknown Entity | PASS |
| Hallucinations | 0 |
