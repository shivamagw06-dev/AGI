# Remediation register: the nine failing gate suites

Owner is the **affected product area**, not whoever wrote the test. Where the
product area is derivable from the code it is named; where the accountable owner
is genuinely unknown it is `UNASSIGNED`. **No name and no date in this document
is invented.**

Source: run `32511791989` (commit `3b84f0b05`), the most recent gate run to
reach a verdict, plus six runs for verdict stability.

## Ownership is not recorded anywhere today

The repository has no `CODEOWNERS` file. The only owner declared in the gate is
`AGI_CORE_OWNER = "Core Platform"` in `ask_product_test/agi_core_v1_0.py`, a
single blanket value for all eighteen suites rather than per-area accountability.

So every `owner` cell below is `UNASSIGNED`. The `product area` column is
derived from what each suite exercises and is offered as the routing hint for
assigning one — not as a substitute for it.

Every `target date` is `UNASSIGNED` for the same reason: a date without the
person who committed to it is decoration.

## Priority: what the defect counters actually say

`core_platform_acceptance` reports its zero-defect gates directly:

| gate | count |
| --- | ---: |
| **Hallucinations** | **4** |
| Recommendation leakage | 0 |
| **Wrong entity** | **0** |
| Wrong sector | 0 |
| **Metadata errors** | **72** |
| Cross-industry leakage | 0 |
| Cross-engine leakage | 0 |

Two things follow, and they are not what the instruction's ordering assumed.

**Hallucinations are live: 4 defects.** This is P0 as directed, and it is a real
non-zero count rather than a precaution.

**Wrong entity is currently clean at 0** on this suite. The entity risk shows up
elsewhere: `company_metadata_routing` scores 51.47%, and metadata errors are the
largest counter at 72. These measure different things — the counter is defects
on core-platform cases, the routing suite is breadth of entity routing — so
"wrong entity" is not currently a defect in the sense the zero-defect gate
measures, while entity *routing* is the worst-scoring suite in the gate.

Both are P0, for different reasons, and conflating them would misdirect the work.

Latency is also outside budget in the same run: `p50=937ms p95=23420ms
within_budget=False`.

## Register

| # | suite | area (derived) | owner | now | target | underlying defect | depends on | date |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| P0 | core_platform_acceptance | Core platform / answer integrity | `UNASSIGNED` | 84.4% | ≥98% + zero defects | 4 hallucinations, 72 metadata errors, p95 latency 23.4s over budget | — | `UNASSIGNED` |
| P0 | company_metadata_routing | Entity resolution / metadata routing | `UNASSIGNED` | 51.47% | 100% | 33 of 68 routing cases fail | likely shares the 72 metadata errors above | `UNASSIGNED` |
| P1 | answer_quality | Answer generation quality | `UNASSIGNED` | 62.4% | ≥95% | 188 of 500 cases below quality bar | may improve with P0 fixes | `UNASSIGNED` |
| P1 | coverage_acceptance | Evidence coverage | `UNASSIGNED` | 54.0% | decision=PASS | 23 of 50 cases uncovered | LLM path (see below) | `UNASSIGNED` |
| P2 | kul_acceptance | Knowledge unification | `UNASSIGNED` | 78.33% | 100% | 13 of 60 cases fail | — | `UNASSIGNED` |
| P2 | founder_evaluation_v2 | Founder evaluation | `UNASSIGNED` | 82.0% | ≥95% | `product_assertion_fail`, `comparison_omits_entity` | LLM path | `UNASSIGNED` |
| P2 | golden_business_20 | Business intelligence | `UNASSIGNED` | 15/20 | 100% | `mention:air india`, `comparison_both`, `institutional_path` | LLM path | `UNASSIGNED` |
| P2 | ii_integration | Industry intelligence integration | `UNASSIGNED` | 87.5% | 100% | 6 of 48 cases fail | — | `UNASSIGNED` |
| P3 | afi_acceptance | AFI routing | `UNASSIGNED` | 86.92% | ≥95% | routing 87.5%, engine_util 87.5%, pollution 12.5% | — | `UNASSIGNED` |

`comparison_omits_entity` in `founder_evaluation_v2` and `mention:air india` in
`golden_business_20` are both entity-completeness failures — a comparison that
silently drops one side. They are P2 by score but share a root with the P0
entity work, and are worth checking against it before being worked separately.

## Which of these block enforcement

Required lane, so a date is needed before the gate can be switched on:

- `core_platform_acceptance` — but only its extracted zero-defect checks; the
  98% score threshold belongs to nightly
- `company_metadata_routing`

Nightly or informational, so an owner is needed but enforcement does not wait:
`answer_quality`, `coverage_acceptance`, `kul_acceptance`,
`founder_evaluation_v2`, `golden_business_20`, `ii_integration`,
`afi_acceptance`.

## The LLM dependency

`founder_evaluation_v2`, `golden_business_20` and `coverage_acceptance` run
through a provider path that logs `OPENAI_API_KEY is not configured` →
`editorial_template_fallback`, with repeated `agib_circuit_open`. Their current
scores are scores *of the fallback*, not of the product. Remediating them
against fallback output may not move the number once a provider is configured,
and could move it the wrong way.

That makes the stub decision a dependency of their remediation, not a separate
piece of tidying.

## What this register does not contain

Names and dates. Both need a person to accept them, and inventing either would
produce a register that looks actionable and is not.
