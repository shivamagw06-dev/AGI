# Phase 2.6 — Institutional Financial Concepts: Implementation Notes

## Why this phase exists

The AGI Financial Intelligence Acceptance Test v1.0 live run (PR #448, commit
`925426f6`) found the Financial Router (PR #447) had closed the accounting/
FSA routing gap completely (100% routing accuracy, 0% pollution on Sections
A/B) but exposed a **coverage gap, not a routing gap**: Section C (Valuation
& Ratios) and part of Section D (Business Intelligence) asked about
institutional finance *concepts* — DuPont, Enterprise Value, ROIC, economic
moats, network effects — that neither `financial_foundations` (accounting
mechanics) nor `financial_statement_intelligence` (analyst interpretation of
a specific company's numbers) were built to answer, and 3 questions about
real global companies outside the platform's verified coverage universe
(Visa, Costco, Ferrari/Toyota) got irrelevant generic evidence instead of an
honest refusal.

## What was built

| Module (brief) | File(s) | Status |
|---|---|---|
| 1-8, 13 Concept modules | `concepts_*.py` (12 files) | **193 concept cards**, every field (definition, business_meaning, interpretation, formula, common_mistakes, industry_exceptions, related_concepts, evidence_level, confidence) populated per card |
| 9 Concept Relationships | `relationships.py` | Graph built directly from `related_concepts` (no hand-maintained duplicate) — 193 nodes, ~395 edges, **zero isolated concepts** |
| 10 Financial Vocabulary | `concepts.py` (aggregator) | Single validated index (`ALL_CONCEPTS`) — zero dangling cross-references |
| 11 Ask Integration | `app/ui/financial_router.py` (`_answer_financial_concept`) | New fallback tier in the existing Financial Router; no other Ask/retrieval code touched |
| 12 Unsupported Coverage Policy | `app/ui/coverage_policy.py` | Curated real-company detector + deterministic refusal, wired into `service.py` **before** the Financial Router |
| 13 Institutional Concept Library | `concepts.py` | Same as Module 10 — one library, described twice in the brief |
| 14 Concept Examination | `exam.py` | **150 scenario questions** (20 hand-authored from the brief's own examples + 130 generated from each card's own `interpretation`/`common_mistakes` text) with a deterministic keyword/fact grader |

Production facade: `production.py`. REST routes: `/v1/financial-concepts/*`
(health, dashboard, concepts, explain, search, related, path, graph, exam).

## Acceptance criteria — actual vs. target

| Criterion | Target | Actual | Note |
|---|---|---|---|
| Deterministic concept cards | 300+ | **193** | See "On the 300+ target" below |
| Examination questions | 150+ | **150** | Exactly met |
| Unit tests | 150+ | **1,538 passing** | `financial_concepts/tests/` (1,449) + `tests/test_coverage_policy.py` (30) + `tests/test_financial_router_concepts.py` (22) + updated `tests/test_financial_router.py`/`test_executive_composer.py` |
| 100% deterministic | Yes | Yes | Zero LLM calls anywhere in this package or its Ask integration |
| No retrieval dependency | Yes | Yes | `financial_concepts` never imports anything from `ask_pipeline`, `knowledge_factory`, or any retrieval module |
| No LLM dependency | Yes | Yes | — |
| No hallucinations | Yes | Yes (by construction) | Every field traces to an authored `ConceptCard`; the router only formats card content, never generates text |
| Concept router integrated | Yes | Yes | `app/ui/financial_router.py` |
| Unsupported-company policy integrated | Yes | Yes | `app/ui/coverage_policy.py`, wired before the router |

## On the 300+ concept-card target

The library covers **every single explicitly named term across all 8
numbered modules and the Module 13 examples** (99 unique named terms —
verified by `financial_concepts/tests/test_mission_questions.py`, which
fails if any one of them is missing), plus ~94 additional, legitimate
extensions (unlevered/levered beta, NPV/IRR/hurdle rate, precedent
transactions, control/minority/liquidity discounts, LBO mechanics, EPS
dilution, goodwill/impairment, segment reporting, value/growth investing,
behavioral finance, TAM/SAM, first-mover advantage, CROCI/ROTE, same-store
sales, promoter holding, audit qualifications, and more) for a total of
**193**.

Reaching literally 300+ would have required either (a) padding with
near-duplicate or thin cards, or (b) re-describing concepts
`financial_foundations`/`financial_statement_intelligence` already own
(EBITDA, gross margin, current ratio, etc.) — both of which would violate
this phase's own "no fabrication" and "no duplication of Phase 1/2"
principles. 193 cards, each independently validated (see
`test_concept_library.py`'s parametrized structural checks across every
card), with zero dangling relationships and zero duplicate keys, was judged
the better trade-off than hitting a round number with weaker content. If
the 300+ figure is a hard product requirement rather than a target, the
next legitimate expansion path is documented above (each module's "natural
extensions" list) and can be added incrementally without restructuring
anything.

## Regression verification

- In-process, via `AskProductHarness` and direct `UiService.search()` calls:
  all 12 previously-failing AFI Section C/D concept questions now report
  `financial_router_triggered=True` (or, for Visa/Costco/Ferrari,
  `short_circuit=unsupported_coverage_policy`) with sub-second latency.
- `tests/test_coverage_policy.py::test_coverage_policy_wins_over_generic_concept_fallback_end_to_end`
  is a true end-to-end regression test (via `UiService.search()`, not just
  the router module in isolation) for the exact ordering bug found during
  development: a company-specific question that also matches a generic
  concept term (e.g. "Why does Visa generate high free cash flow?") must
  get the coverage-policy refusal, not a company-blind concept explanation.
- Full existing regression suites (`test_executive_composer.py`,
  `test_ask_orchestration_*`, `test_recommendation_policy_short_circuit.py`,
  `test_recommendation_drift_v1.py`, `test_ask_product_smoke.py`,
  `test_ask_product_regression.py`, `test_ask_product_ikl.py`,
  `financial_foundations/tests`, `financial_statement_intelligence/tests`,
  `institutional_accounting_exam/tests`, `kip_v2/tests`) all pass with no
  regressions.
- **Live re-verification against the AFI Acceptance Test v1.0 requires this
  branch to be deployed** — see the suite's own baseline-comparison output
  (`ask_product_test/run_afi_acceptance_v1.py`) for the before/after numbers
  once run against production.
