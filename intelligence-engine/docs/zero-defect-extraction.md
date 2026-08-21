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

---

# Report-only short gate

`ask_product_test/run_short_gate.py`. Blocks nothing: no required check, no
branch protection, no deployment dependency, and a budget overrun is reported
rather than failed.

## The universe, not the current count

4 hallucinations and 2 wrong-company bindings are what is broken today. A gate
scoped to those would pass the moment they were fixed and would not notice the
seventh defect.

It runs **every** `J_impossible` case and **every** identity-bearing case —
**395 of the bank's 500** (50 + 345) — and requires the defect counters at zero
across all of them.

## A missing stub is infrastructure, never NOT_RUN

`NOT_RUN` is a legitimate outcome for optional live-provider evaluation. In a
deterministic required lane it is not: a lane that downgrades to "did not run"
when its determinism source is missing reports nothing while looking like it
found nothing. Failing to install the stub exits `2`.

The same applies to `ASK_TEST_MODE`. In `contract` mode the harness answers
without reaching the engine — this was caught while building it: a local run
reported `decision=PASS zero_defect=True` in **0.0 seconds** with 20 of 20 cases
failing for one reason. A green result produced by not running the product. The
gate now refuses to start outside `inprocess`.

## Cases and labels are counted separately

`unique_failing_cases`, `unique_p0_cases` and `label_occurrences` are reported
independently. One case can carry several labels; counting labels as cases
overstates the problem and counting cases as labels hides which problems are
present.

## Routing and missing metadata are kept, and are not P0

They appear in `non_p0_categories` and in `by_category`, and they do not affect
`zero_defect` or the decision. They are real, tracked, and do not make a release
unsafe.

## What is not verified

**The runtime.** The engine cannot be exercised locally — it needs the workflow's
environment and its acceptance-data bootstrap — so the 13–15 minute target is
unmeasured. The long suite costs 3.44 s/case over 500 cases; at that rate 395
cases would be 22.6 minutes, over budget. The stub removes the provider latency
tail, which is the plausible cause of the suite's `p95=23420ms` against
`p50=937ms`, and at p50 the same 395 cases would be about 6 minutes.

Both are extrapolations. The first CI run measures it, and `SHORT_GATE_BUDGET_SEC`
makes the ceiling adjustable once a real number exists. If it lands over budget,
the remedy is a decision about scope — not a smaller case set chosen to fit,
which would reintroduce exactly the "current count as universe" error.
