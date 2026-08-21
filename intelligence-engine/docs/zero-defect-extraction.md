# Zero-defect extraction

Report-only. **Blocks no merge and no deployment.** Wiring it into a required
gate is a separate decision, taken after the extraction is demonstrably complete.

## Provisional section mapping

**Provisional until an accountable product owner approves it.** This is read out
of `core_platform_acceptance_v1.evaluate_case` — it records where each flag is
raised *today*, not where it ought to be.

| defect | raised in | confinable |
| --- | --- | --- |
| `hallucination` | `J_impossible` only | yes |
| `metadata_error` | `A_company_identity`, `I_metadata` | yes |
| `recommendation_leakage` | `E_investment` | yes |
| `wrong_entity` | wherever a case resolves an identity | **no** |
| `wrong_sector` | same | **no** |
| `cross_industry_leakage` | same, via `validate_text` | **no** |

`wrong_entity` cannot be extracted by section filter. It fires on any case that
carries a ticker whose resolved identity disagrees with the claim, so a
section-scoped run would under-report it. The extract keeps every
identity-bearing case rather than pretending a subset covers it, and reports
`not_section_confined` so a reader can see which properties that applies to.

## Hallucination checks: the four defects are still detected

The gate run counted 4 hallucinations. The per-case artifact names them:
`no_honest_uncertainty` ×4, all in `J_impossible`.

The extract asserts this rather than describes it. A deterministic stub produces
a fabricating answer; the detector flags it; four such answers among twenty
honest ones are reported as exactly four, and the decision is FAIL. Twenty
honest answers with none fabricating report zero and PASS.

A stub that could only produce good answers would prove nothing, so it produces
both.

## `company_metadata_routing`: 51.47% is not 33 P0 defects

The aggregate said 35/68. The per-case artifact says 33 failing cases carrying
45 labels, and they are not one problem:

| category | labels | |
| --- | ---: | --- |
| routing | **37** | never reached the metadata engine, or reached it as the wrong intent or from the wrong sources |
| missing metadata | 6 | reached it, no value came back |
| **wrong company** | **2** | `bound_namesake` — bound to the wrong entity |

**Release-critical: 2, not 33.** The 37 routing labels are one defect seen from
three angles; fixing the routing likely moves most of the score at once. The two
namesake bindings are the cases that make a release unsafe, and under an
aggregate reading they would have competed for attention with 37 labels of a
different problem.

Neither `incomplete_comparison` nor `formatting` appears in this suite. Those
labels live in `founder_evaluation_v2` (`comparison_omits_entity`) and
`golden_business_20` (`comparison_both`) — the taxonomy carries them so the same
classifier covers those suites, but they are empty here rather than invented.

## The same reading corrects the register

`core_platform_acceptance`'s 72 "metadata errors" are all `not_metadata_route` —
routing, one root cause, not 72 distinct data defects:

| category | labels |
| --- | ---: |
| routing | 72 |
| hallucination | 4 |
| formatting | 2 |

So both P0 rows in the remediation register are, in their bulk, the same routing
defect. The genuinely release-critical residue is 4 hallucinations and 2
wrong-company bindings.

## Missing provider is never a product score

An extract run with no editorial credential returns `decision: NOT_RUN` with a
reason, not a score of zero and not a PASS. Clean output from template fallback
is still fallback output: it measures the absence of a credential, not the
product.

`provider_configured()` checks `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`. A test asserts that even entirely clean results report
`NOT_RUN` when no provider is configured.

## Deterministic stub for required checks

`ask_product_test/provider_stub.py` returns fixed answers for fixed questions.
Required checks run against it so what is enforced is the pipeline's own logic
rather than a provider's variance or a credential's absence. Live-provider
evaluation stays nightly, where variance is the signal.

The stub fills `answer.summary`, which is what `checks.extract_answer_text`
reads. Filling `answer.text` instead produces empty answer text and every case
fails for the wrong reason — worth stating because it is the sort of mistake
that makes a check look strict while testing nothing.

## What is not done

The extract is not wired into any workflow, required lane, or branch protection.
The section mapping needs an owner's sign-off. The short gate is built around
this once the extraction is accepted.
