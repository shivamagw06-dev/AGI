# Phase X — AGI Knowledge Unification Layer (KUL)

## Objective

Make every existing knowledge source reachable through one deterministic
orchestration layer. **No new datasets. No LLM.**

## Package

`intelligence-engine/knowledge_unification/`

| Module | Role |
|---|---|
| `registry.py` | Knowledge Source Registry |
| `query_planner.py` | Question typing (company/concept/accounting/…) |
| `knowledge_planner.py` | Ordered provider plan (never blind retrieval) |
| `providers/*` | Thin wrappers over existing engines |
| `ranking.py` | Reject empty / duplicate / errored results |
| `fusion.py` | Evidence fusion + coverage object |
| `company_object.py` | Canonical Company Intelligence object |
| `production.py` | `plan_and_gather` / Ask `answer_for_ask` |

## Providers registered

`capiq_ikt`, `ikl`, `company_memory`, `knowledge_factory`, `cgl`,
`financial_concepts`, `financial_foundations`, `financial_statement_intelligence`,
`academy`, `legacy_kip` (fallback only).

## Ask integration

In `app/ui/service.py`, after unsupported-coverage refusal and before the
isolated IKT company router / financial router:

```
coverage_policy → KUL (fused) → company_router fallback → financial_router fallback → …
```

Orchestration fields: `short_circuit=knowledge_unification`,
`kul_providers_used`, `kul_coverage`, `kul_diagnostics`.

KUL short-circuits Ask only when a **hard** provider contributed
(CapIQ / memory / IKL / KF / CGL / financial engines). Soft-only academy
or legacy hits fall through so unknown-entity and CapIQ routers still run.

## CapIQ field unlock

The CapIQ provider surfaces previously stored-but-unused fields into
Ask answers: returns series, earnings dates, products, parent, investors,
website — fused with memory/KF/CGL when available.

## API

- `GET /api/knowledge-unification/health`
- `GET /api/knowledge-unification/registry`
- `POST /api/knowledge-unification/plan` `{question, ticker?}`

## Acceptance (in-process)

| Suite | Result |
|---|---|
| KUL Acceptance (60) | **60/60 PASS** |
| Concept Acceptance (12) | **12/12 PASS** |
| AFI routing / engine / pollution / reco / unknown | **100% / 100% / 0% / 100% / 100%** |
| AFI overall score | 83.5% (quality scores; gate ≥95 still open on interpretive depth) |
| Coverage Acceptance | 45/50 — remaining NSE-04/NSE-15 pre-existing; BSE NSE-twin accepts added |
| Golden Founder 5 | 3/5 — GF5-02/03 substance gaps (KF/comparison), policy paths green |

## Guardrails landed in this phase

- Pedagogy questions do not keep fuzzy CapIQ binds (`advance` ≠ ADVANCE).
- CapIQ provider trusts the Knowledge Plan ticker (no re-detect).
- Financial Concepts alias match is word-bounded (`ev` ∉ `every`).
- Company Memory soft-timeout (1s, non-blocking shutdown).
- Target-price questions hit recommendation policy.

## Deferred / next

- Industry playbooks + valuation engine as first-class providers.
- kip_v2 provider once the store has documents.
- Damodaran spreadsheet *numeric* cells as structured academy facts.
- Raise AFI overall quality on interpretive FSA / "PAT doubled" shapes.
