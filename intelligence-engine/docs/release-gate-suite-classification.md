# Release gate: suite classification matrix (step 2)

Which suites belong in a required gate, and separately, when that gate can be
enforced. **Lane membership is by release risk. Enforcement readiness is a
different column and must not be allowed to decide membership.**

## Correction to the first version of this matrix

The first version chose the required lane by picking the eight suites that
currently pass. That is a gate that is green by construction: it enforces only
what already succeeds, and it quietly demoted `core_platform_acceptance` — which
carries the hallucination and wrong-entity gates — to nightly because it is slow
and failing. Those are the two properties that make a check worth requiring.

The rule that produced it ("a suite that has never passed cannot be required")
conflated membership with readiness. A suite that guards a release-critical
property belongs in the required lane whatever it currently scores; what its
score decides is *when enforcement switches on*, not whether it is listed.

## Lanes

| lane | purpose | enforcement |
| --- | --- | --- |
| **Required preflight** | fast, deterministic, release-critical | blocks merge once ready |
| **Required zero-defect** | hallucination and wrong-entity checks, extracted from the long suite | blocks merge once ready |
| **Nightly evaluation** | long-form quality scoring, live-provider behaviour | reports trends, blocks nothing |
| **Informational baseline** | currently failing, awaiting product remediation | visible, blocks nothing |

## Matrix

`ready` means the suite could be enforced today: it passes, and its determinism
is by design rather than by accident.

| suite | sec | verdict ×6 | deterministic | ext. deps | lane | ready |
| --- | ---: | --- | --- | --- | --- | --- |
| core_platform_acceptance | 1,719.5 | FAIL ×6 | stable | harness | **required zero-defect** (extract) + nightly (rest) | no — failing |
| answer_quality | 1,402.8 | FAIL ×6 | stable | harness | nightly | n/a |
| founder_evaluation_v2 | 260.0 | FAIL ×6 | stable | http, **llm** | nightly | n/a |
| golden_business_20 | 153.7 | FAIL ×6 | stable | **llm** | nightly | n/a |
| coverage_acceptance | 70.0 | FAIL ×6 | stable | http, **llm** | informational baseline | no — failing |
| golden_founder_5 | 58.3 | PASS | stable | http | required preflight | yes |
| bi_integration | 58.0 | PASS ×6 | stable | **llm** | required preflight | **no — llm** |
| canonical_classification | 54.3 | PASS ×6 | stable | none | required preflight | yes |
| kul_acceptance | 28.0 | FAIL ×6 | stable | none | informational baseline | no — failing |
| ii_integration | 10.5 | FAIL ×6 | stable | none | informational baseline | no — failing |
| company_metadata_routing | 8.7 | FAIL ×6 | stable | none | **required preflight** (entity routing) | no — failing |
| afi_acceptance | 8.2 | FAIL ×6 | stable | http | informational baseline | no — failing |
| founder_evaluation_v3 | 4.7 | PASS ×6 | stable | **llm** | required preflight | **no — llm** |
| concept_acceptance | 4.2 | PASS ×6 | stable | http | required preflight | yes |
| bi_acceptance | 1.3 | PASS ×6 | stable | none | required preflight | yes |
| recommendation_policy | 1.2 | PASS ×6 | stable | none | required preflight | yes |
| unknown_entity | 1.2 | PASS ×6 | stable | none | required preflight | yes |
| ii_acceptance | 0.2 | PASS ×6 | stable | none | required preflight | yes |

`company_metadata_routing` is listed as required and not ready: wrong-entity
routing is a release-critical property, and it currently scores 51.47%. That row
is the point of separating the two columns — under the previous rule it would
have been silently dropped for failing.

## The five LLM-dependent suites

`founder_evaluation_v2`, `golden_business_20`, `bi_integration`,
`founder_evaluation_v3`, `coverage_acceptance`.

Gate logs show `OPENAI_API_KEY is not configured` → `editorial_template_fallback`,
with repeated `agib_circuit_open`. These suites are stable across six runs
*because the key is absent and the failure is total*. That is determinism by
accident: configure a key and their behaviour changes in ways six runs of
fallback-mode evidence cannot predict.

None should be required in this state. A required version needs deterministic
fixtures or a controlled provider stub, so that what is enforced is the suite's
own logic rather than the current absence of a credential. Live provider
behaviour belongs in nightly, where variance is a signal rather than a blocker.

Two of them — `bi_integration` and `founder_evaluation_v3` — pass today and
would have been swept into a required lane on pass status alone.

## Extracting the zero-defect checks

`core_platform_acceptance` declares seven defect gates: hallucinations,
recommendation leakage, wrong entity, wrong sector, metadata errors,
cross-industry leakage, cross-engine leakage. It scores 500 cases across ten
sections (`A`–`J`, including `I_metadata` and `J_impossible`) and exits 0 only
at ≥98% *with zero defects*.

Cases are generated per section in `core_platform_acceptance_v1.py` rather than
loaded from a fixture bank, so a section-scoped run is mechanically feasible —
the section is already a field on every case. A required extract would run the
defect-bearing sections at a reduced case count and assert the defect counters
are zero, leaving the 98% score threshold to nightly.

This is a feasibility finding, not a design. Which sections carry which defect
gate, and how many cases are enough to catch a regression, needs the suite's
owner.

## Determinism

Across six completed runs: nine suites failed every time, eight passed every
time, none flipped. The failures are standing product gaps rather than
flakiness. That is what makes step 6's three-consecutive-successes bar
meaningful — these verdicts do not move on their own, so three passes would
represent real change.

## Enforcement readiness

Six suites are ready today: `golden_founder_5`, `canonical_classification`,
`concept_acceptance`, `bi_acceptance`, `recommendation_policy`, `unknown_entity`
— 120.5 seconds combined.

That set is not the required lane. It is the subset of the required lane that
could be switched on now, and enforcing only it would reproduce the original
mistake in a smaller form. The required lane also contains
`company_metadata_routing` (failing), the extracted zero-defect checks (not yet
built), and two LLM-dependent suites (needing a stub) — and enforcement waits on
those, or on an explicit re-approval of their thresholds by their owners.

## Open questions for product owners

1. Are the nine failing suites defects with owners and dates, or aspirational
   benchmarks? The answer decides whether the required lane is weeks or quarters
   from enforceable.
2. Which `core_platform_acceptance` sections carry the hallucination and
   wrong-entity gates, and what case count catches a regression?
3. Should CI pin the LLM path to a stub so determinism is deliberate?
4. Is `company_metadata_routing` at 51.47% a threshold problem or a product
   problem?
