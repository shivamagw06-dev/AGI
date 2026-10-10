# RQ1 Research Ontology — Constitution (Sprint 1)

**Status:** LOCKED foundation for RQ1  
**Rule:** Taxonomy mistakes propagate. Change only via explicit constitution revision.  
**Scope:** Classify research type **before** any analyst or intelligence layer executes.  
**Architecture:** Soft-wire supporting ontology — **not** a new top-level intelligence layer after IDE V2.

---

## First question AGIB must ask

> What type of research is this?

Not: What is the answer?

---

## Primary Intent (exactly one)

| Intent ID | Label | Objective |
|---|---|---|
| `company_research` | Company Research | Investment Evaluation |
| `sector_research` | Sector Research | Relative Attractiveness |
| `index_research` | Index Research | Historical Valuation |
| `macro_research` | Macro Research | Macro Impact Assessment |
| `portfolio_research` | Portfolio Research | Allocation Decision |
| `company_comparison` | Company Comparison | Relative Company Evaluation |
| `screening` | Screening | Universe Filter |
| `forecast` | Forecast | Scenario Analysis |
| `risk` | Risk | Downside Analysis |
| `valuation` | Valuation | Fair Value Assessment |
| `technical` | Technical | Price Structure Analysis |
| `educational` | Educational | Concept Teaching |
| `news` | News | Impact Assessment |

Exactly **one** primary intent per question.

---

## Secondary Intents (zero or many)

Supporting modifiers / lenses. Examples: `valuation`, `risk`, `forecast`, `long_term`, `short_term`, `portfolio`, `historical_comparison`, `macro`, `peer`, `earnings`.

---

## Entity Types

Company · Sector · Index · ETF · Commodity · Currency · Bond · Country · Macro Variable · Theme · Portfolio · Watchlist · Person · Event

---

## Mandatory classifier output

```yaml
question_type
primary_intent
secondary_intents
entity
entity_type
research_objective
confidence
requires_clarification
possible_matches   # when clarification required
next_stage
executed_layers    # always [] in Sprint 1
executed_analysts  # always [] in Sprint 1
```

---

## Sprint 1 law

No research begins when clarification is required.  
No analyst or intelligence layer executes in Sprint 1 classification.
