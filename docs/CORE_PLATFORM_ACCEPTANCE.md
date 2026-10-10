# AGI Core Platform Acceptance v1.0

**Priority:** P0 — highest release gate
**Runner:** `ask_product_test/run_core_platform_acceptance_v1.py`

Individual engine suites verify each subsystem. This suite verifies that
Company Identity, Financial, Business, Industry, Investment, Research,
Consensus Intelligence and Knowledge Unification behave as **one institutional
platform** from a user's point of view. Every PR must pass it before merge.

## Shape

500 questions, 50 per section, run through the real Ask pipeline
(`UiService.search`, in-process).

| Section | Focus |
|---|---|
| A | Company Identity |
| B | Financial Intelligence |
| C | Business Intelligence |
| D | Industry Intelligence |
| E | Investment Intelligence |
| F | Research Intelligence |
| G | Consensus Intelligence |
| H | Knowledge Unification |
| I | Metadata |
| J | Impossible Questions |

Sections A, C, E, F, G, H and I are generated across the **33 golden
companies**, so every release tests all of them across all 11 primary sectors.

## Gate

Overall **≥98%** *and* every zero-defect counter at zero:

hallucinations · recommendation leakage · wrong entity · wrong sector ·
wrong company · metadata errors · cross-industry leakage · cross-engine leakage

Latency is measured and reported (P50 700ms / P95 3000ms / average 1500ms
targets) but does not by itself block the gate, since the harness runs
in-process with cold caches.

## Current certification

```
500/500 (100%)  decision=PASS
A 100  B 100  C 100  D 100  E 100
F 100  G 100  H 100  I 100  J 100
hallucinations 0   recommendation leakage 0
wrong entity 0     wrong sector 0
metadata errors 0  cross-industry leakage 0
cross-engine leakage 0
latency p50 440ms · p95 2660ms · avg 889ms
```

## Artifacts

`artifacts/core_platform_acceptance_v1.{json,md,html}` — machine-readable
report, a Markdown summary, and a styled HTML scorecard with section scores,
zero-defect gates, latency and any failures.

## Product bugs this suite caught

Building it surfaced four real defects, all fixed:

1. **Consensus questions were refused as trade requests.** "What is the
   consensus target price for Axis Bank?" hit the no-recommendations policy
   because it contains "target price". Asking what the sell side thinks is
   market data, so `is_recommendation_query` now yields to consensus,
   analyst, broker and street phrasing unless the user asks AGI for its own
   call.
2. **Accounting pedagogy was treated as a company.** "Why does every
   transaction require a debit and a credit?" reached Entity Intelligence and
   was refused. Concept detection now covers "why does/do" and accounting
   vocabulary.
3. **Company names containing field words hijacked the metadata router.**
   "What did Reliance Industries's annual report say?" was answered as a
   request for Reliance's primary industry. Field words are now detected only
   outside the resolved company name.
4. **Group and brand stems bound a namesake.** "Explain Apollo" answered for
   Apollo Micro Systems and "Explain Birla" for Birla Corporation. Stems that
   match several registry companies now return a clarification listing the
   candidates, and one-word forms that only exist because a legal suffix was
   stripped ("Birla Corporation" → "Birla") no longer bind.

## Release pipeline

Registered in `run_production_regression_v1.py` after the identity gates:

```
… engine suites → canonical classification → company metadata routing
→ core platform acceptance → PASS → merge
```
