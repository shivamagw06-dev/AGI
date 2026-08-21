# Release gate: measured suite timings

Evidence for the suite classification decision (step 2). **This document does not
classify anything** — which suites are release-critical is a product-owner call,
not one the measurements can make. It records what the suites cost.

Source: run `32511791989`, commit `3b84f0b05`, the most recent gate run to reach
a verdict. 18 suites, 3,845s of child-process time, `decision=FAIL 7/18`.

| suite module | exit | seconds | share |
| --- | ---: | ---: | ---: |
| run_core_platform_acceptance_v1 | 1 | 1,719.5 | 44.7% |
| run_answer_quality_acceptance_v1 | 1 | 1,402.8 | 36.5% |
| run_founder_evaluation_v2 | 1 | 260.0 | 6.8% |
| run_golden_business_20 | 1 | 153.7 | 4.0% |
| run_coverage_acceptance_v1 | 1 | 70.0 | 1.8% |
| run_golden_founder_5 | 0 | 58.3 | 1.5% |
| run_bi_integration_acceptance_v1 | 0 | 58.0 | 1.5% |
| run_canonical_classification_acceptance_v1 | 0 | 54.3 | 1.4% |
| run_kul_acceptance_v1 | 1 | 28.0 | 0.7% |
| run_ii_integration_acceptance_v1 | 1 | 10.5 | 0.3% |
| run_company_metadata_routing_acceptance_v1 | 1 | 8.7 | 0.2% |
| run_afi_acceptance_v1 | 1 | 8.2 | 0.2% |
| run_founder_evaluation_v3 | 0 | 4.7 | 0.1% |
| run_concept_acceptance_v1 | 0 | 4.2 | 0.1% |
| run_bi_acceptance_v1 | 0 | 1.3 | 0.0% |
| run_recommendation_policy_acceptance_v1 | 0 | 1.2 | 0.0% |
| run_unknown_entity_acceptance_v1 | 0 | 1.2 | 0.0% |
| run_industry_intelligence_acceptance_v1 | 0 | 0.2 | 0.0% |

## What the distribution says

**Two suites are 81.2% of wall time.** `core_platform_acceptance` (28.7 min) and
`answer_quality` (23.4 min) together run 52 minutes; the other sixteen total
12 minutes.

**Thirteen suites finish inside 60 seconds**, totalling 239s.

A gate in the region of ten minutes is therefore reachable by moving those two
suites out of it, without dropping any of the other sixteen. That is a
consequence of the measurements; whether it is the right split depends on which
suites are meant to block a release, which this document does not decide.

## Run history

Across the last 100 runs of this workflow: **82 cancelled, 14 failed, 0 passed.**
Completed runs took 61–82 minutes against a 90-minute job ceiling.

The cancellations are concurrency, not flakiness. The group key is
`production-release-${{ github.workflow }}-${{ github.ref }}` with
`cancel-in-progress: true`, so a second push to the same ref kills the first run
— and pushes arrive faster than a 70-minute job completes. Different refs are
different groups, so PR runs and main runs proceed in parallel rather than
cancelling each other.

## Failing suites in that run

`founder_evaluation_v2` 82.0, `golden_business_20` 15/20, `afi_acceptance`
86.92, `ii_integration` 87.5, `coverage_acceptance` 54.0,
`kul_acceptance` 78.33, `company_metadata_routing` 51.47,
`core_platform_acceptance` 84.4, `answer_quality` 62.4.

Reported verdict: `merge_allowed=False`, product failure reason
`founder_evaluation_v2 below threshold (actual=82.0)`.

These are standing product gaps. Nothing here proposes changing a threshold.
