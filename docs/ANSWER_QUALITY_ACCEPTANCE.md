# AGI Answer Quality Acceptance v1.0 (Phase 4.0)

**Runner:** `ask_product_test/run_answer_quality_acceptance_v1.py`
**Status:** not yet certified — **95.6%** against the Phase 4.1 target of 97%.

Core Platform Acceptance proves AGI answers *safely*: right route, right
entity, no hallucination, no recommendation leakage. It does not prove AGI
answers *well*. This suite measures institutional depth, company specificity,
evidence quality, research depth and executive communication, and fails
answers that are technically correct but generic.

## Shape

500 questions, 50 per section, scored on nine weighted dimensions rather than
routing and length.

| Dimension | Weight |
|---|---|
| Answers the actual question | 20 |
| Company specificity | 15 |
| Evidence quality | 15 |
| Financial reasoning | 15 |
| Industry specificity | 10 |
| Executive communication | 10 |
| Research depth | 10 |
| Boilerplate penalty | 5 |
| Honest uncertainty | 5 |

A case passes at ≥70 quality with no automatic fail. Automatic fails:
boilerplate, generic investment thesis, generic research answer, industry
refusal, wrong evidence, company answered generically, recommendation leakage,
unexpected refusal.

**Boilerplate detection** compares answers to the same template across
different companies; similarity ≥0.85 fails both. Axis Bank, ICICI Bank and
SBI cannot share one thesis.

## Current result (after Phase 4.1)

```
478/500 (95.6%)  target 97%  decision=FAIL

A Company Intelligence     96%   F Research Intelligence     94%
B Financial Intelligence   96%   G Consensus Intelligence    96%
C Business Intelligence    98%   H Knowledge Fusion          86%
D Industry Intelligence    92%   I Executive Communication  100%
E Investment Intelligence  94%   J Impossible Questions     100%

boilerplate 8 · generic thesis 2 · generic research 1 · industry refusal 0
wrong evidence 0 · company answered generically 2 · recommendation leakage 0
```

Trajectory: **53.3% → 90.4% (Phase 4.0) → 95.6% (Phase 4.1)**.

## Product defects this suite found and fixed

1. **Provider names leaked into answers.** Every fused answer carried
   "Sources fused: industry_intelligence, business_intelligence, capiq_ikt…".
   Internal plumbing now stays in diagnostics.
2. **Company questions were answered with industry templates.** "Explain Axis
   Bank" led with "For banks, enterprise value is primarily driven by NIM,
   CASA…" — true of every bank, so about none. A company-bound answer must now
   mention the company, otherwise fusion picks the first provider summary that
   does.
3. **Industry pedagogy was refused for want of an entity.** "How are banks
   valued?" and "What KPIs matter for telecom?" hit the unknown-entity policy.
   Industry pedagogy is now a first-class route.
4. **Research questions were answered with company profiles.** "What did Axis
   Bank's annual report say?" returned a business description as if it were
   the report. When research memory holds no filed document, the answer now
   says so before offering what is on file.
5. **"What does X do?" refused for every company.** The canonical registry bind
   was gated behind a bare-stem guard. Since the resolver only binds exact or
   unambiguous names, that guard is gone.

## Remaining work to certify

- **Knowledge Fusion (72%)** — multi-provider questions still lean on one
  provider instead of composing identity, business, industry, consensus and
  research into one view.
- **Investment thesis depth** — companies without a curated thesis fall back to
  consensus plus industry DNA, so bank theses read alike. Three still trip the
  generic-thesis gate and several cluster as boilerplate.
- **Financial reasoning (33%)** — concept answers state definitions without
  the causal chain the dimension looks for.
- **Industry specificity (56%)** — company answers rarely carry the industry's
  own KPI vocabulary.

## Artifacts

`artifacts/answer_quality_acceptance_v1.{json,md,html}` — section heatmap,
quality gates, dimension averages, weakest companies, boilerplate clusters and
the worst 50 answers with text.

## Pipeline

Registered after Core Platform Acceptance:

```
production regression → core platform acceptance → answer quality acceptance
```

## Phase 4.1 — Institutional Answer Intelligence

Fusion 2.0 replaced "pick one provider's summary" with objective-led
composition:

- **The question's objective decides who leads.** A consensus question is led
  by consensus, a research question by research, a thesis by investment
  intelligence, a business question by the company's own profile.
- **Industry cards can no longer lead a company answer.** Both template shapes
  ("For banks, enterprise value is primarily driven by…" and "Banks economics:
  revenue from…") are rejected as leads when a company is bound.
- **Company specificity is proven, not assumed.** Industry words are excluded
  from the company's own name tokens, so "cement" no longer makes a cement
  industry card look like an answer about UltraTech Cement.
- **Concept pedagogy no longer needs an entity.** "Explain the difference
  between accrual and cash profit" was refused by the bare-stem guard.

Section movement: Knowledge Fusion 72% → 86%, Company Intelligence 80% → 96%,
Executive Communication 90% → 100%, Consensus 88% → 96%, Investment 90% → 94%.
Wrong evidence went 5 → 0.

### Remaining work to reach 97%

- **Boilerplate (8 clusters)** — companies without a curated thesis still share
  wording. Needs Investment Intelligence to generate per-company theses
  (Workstream 2), which is an engine change rather than a composition change.
- **Financial reasoning (33%)** — concept answers give definitions where the
  dimension expects causal chains (Workstream 6).
- **Industry specificity (56%)** — company answers rarely carry the industry's
  own KPI vocabulary.
- **Knowledge Fusion (86%)** — multi-part questions ("business, industry
  position and what the street thinks") still answer one part well rather than
  composing all three (Workstream 1's section planner).

## Phase 4.2 — Company Thesis Intelligence

A synthesis layer inside Investment Intelligence
(`investment_intelligence/company_thesis.py`) composes a twelve-section
institutional thesis for any covered company from evidence that already
exists: canonical identity, CapIQ profile, reported financials, market
consensus, and the company's position relative to its industry peers.

Uniqueness is structural rather than stylistic. Two banks differ because their
scale rank, margin, coverage, target dispersion, momentum and named
competitors differ, and every section is written from those numbers.

Measured similarity across full theses:

| Pair | Similarity | Threshold |
|---|---|---|
| Axis Bank vs ICICI Bank | 0.11 | <0.70 |
| Axis Bank vs HDFC Bank | 0.05 | <0.70 |
| Axis Bank vs Infosys | 0.02 | <0.60 |
| Infosys vs Reliance | 0.05 | <0.60 |

Risks and catalysts are derived from the company's own position — Axis Bank's
29% implied upside against a 17.8% peer median reads differently from
Infosys trailing its peer median on 18 of 42 positive brokers.

Fusion also now orders supporting reasoning behind whichever provider
answered, so a company thesis is followed by its own evidence rather than
another engine's industry notes.

Result: **95.6% → 96.2%**, Consensus 96% → 100%, Research 94% → 96%,
boilerplate 8 → 6. Regression: `investment_intelligence/tests/test_company_thesis.py`.
