# Release gate: suite classification matrix (step 2)

Evidence for deciding which suites belong in a short required gate and which
belong in a nightly evaluation lane. The **proposed lane column is a proposal,
not a decision** — release risk is a product-owner judgement, and the columns
left of it are what the measurements can actually support.

Sources: run `32511791989` for durations; six completed runs for verdict
stability; static inspection of each suite module for dependencies.

## Matrix

| suite | sec | share | verdict (6 runs) | deterministic | external deps | proposed lane |
| --- | ---: | ---: | --- | --- | --- | --- |
| core_platform_acceptance | 1,719.5 | 44.7% | FAIL ×6 | stable | harness only | **nightly** |
| answer_quality | 1,402.8 | 36.5% | FAIL ×6 | stable | harness only | **nightly** |
| founder_evaluation_v2 | 260.0 | 6.8% | FAIL ×6 | stable | http, llm | **nightly** |
| golden_business_20 | 153.7 | 4.0% | FAIL ×6 | stable | llm | **nightly** |
| coverage_acceptance | 70.0 | 1.8% | FAIL ×6 | stable | http, llm | nightly |
| golden_founder_5 | 58.3 | 1.5% | PASS | stable | http | required |
| bi_integration | 58.0 | 1.5% | PASS ×6 | stable | llm | required |
| canonical_classification | 54.3 | 1.4% | PASS ×6 | stable | none | required |
| kul_acceptance | 28.0 | 0.7% | FAIL ×6 | stable | none | nightly |
| ii_integration | 10.5 | 0.3% | FAIL ×6 | stable | none | nightly |
| company_metadata_routing | 8.7 | 0.2% | FAIL ×6 | stable | none | nightly |
| afi_acceptance | 8.2 | 0.2% | FAIL ×6 | stable | http | nightly |
| founder_evaluation_v3 | 4.7 | 0.1% | PASS ×6 | stable | llm | required |
| concept_acceptance | 4.2 | 0.1% | PASS ×6 | stable | http | required |
| bi_acceptance | 1.3 | 0.0% | PASS ×6 | stable | none | required |
| recommendation_policy | 1.2 | 0.0% | PASS ×6 | stable | none | required |
| unknown_entity | 1.2 | 0.0% | PASS ×6 | stable | none | required |
| ii_acceptance | 0.2 | 0.0% | PASS ×6 | stable | none | required |

## Determinism

**Every suite is stable.** Across six completed runs, nine failed every time and
eight passed every time, with no suite flipping. `golden_founder_5` appears in
fewer runs because of a differing log format, not instability.

So the failures are standing product gaps, not flakiness — which matters for
step 6: three consecutive successful runs is a meaningful bar precisely because
these verdicts do not move on their own.

## External dependencies

Every suite goes through `ask_product_test.harness`, which under
`ASK_TEST_MODE=inprocess` calls the engine directly rather than over HTTP. The
`http` column marks modules that import urllib at all; in-process mode means
those paths are mostly unused during the gate.

The `llm` column is the one that matters. Gate logs show
`editorial_provider_failed ... OPENAI_API_KEY is not configured` followed by
`editorial_template_fallback`, and repeated `agib_circuit_open`. LLM calls are
attempted, fail, and fall back to templates. That is *currently* deterministic
because the key is absent in CI and the failure is total — but it is
deterministic by accident. Configure a key and these suites become
non-deterministic in a way the six-run sample cannot predict.

Five suites touch that path: `founder_evaluation_v2`, `golden_business_20`,
`bi_integration`, `founder_evaluation_v3`, `coverage_acceptance`. Two of them
sit in the proposed required lane.

## What the proposed lane is based on

Only two rules, both mechanical:

1. A suite that has never passed cannot be in a required gate — it would block
   every merge on day one.
2. A suite costing minutes of wall time belongs in the nightly lane regardless
   of verdict.

Everything else is a product judgement this document does not make. In
particular: whether `core_platform_acceptance`'s zero-defect gates
(hallucination, wrong entity) are too important to relegate to nightly, even at
28.7 minutes, is exactly the sort of question the timings cannot answer.

## Cost of the proposed required lane

Eight suites: 0.2 + 1.2 + 1.2 + 1.3 + 4.2 + 4.7 + 54.3 + 58.0 + 58.3 = **183.4
seconds** of suite time.

Against the full 18 at 3,845s, that is 4.8%. Adding job overhead — checkout,
Python setup, dependency install, acceptance bootstrap, health check, artifact
upload — a required gate of this shape lands well inside ten minutes.

Note this is a **smaller** set than "everything except the two slow suites",
which was 723s and 13-15 minutes with overhead. The difference is the nine
always-failing suites: they cannot be required until they pass, whatever their
duration.

## Open questions for product owners

1. Are the nine currently-failing suites aspirational benchmarks, or defects
   with owners and dates?
2. Does `core_platform_acceptance`'s zero-defect requirement need to block
   merges, and if so at what runtime cost?
3. Should the LLM-dependent suites be pinned to template fallback in CI so their
   determinism is deliberate rather than incidental?
4. If a nightly lane reports score trends, who acts on a regression, and does a
   trend break block anything?
