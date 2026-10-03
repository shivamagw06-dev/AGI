# AGI Institutional Investor Curriculum v1.0

**Document type:** Editorial Benchmark Curriculum  
**Layer:** Institutional Research Engine (IRE)  
**Status:** Execution Program  
**Architecture:** Frozen — research quality and communication only  

---

## Purpose

Teach AGI how institutional investors think, research, communicate, and make decisions.

This curriculum is **not company specific**. It defines the universal questions every institutional investor asks before committing capital.

No new intelligence engines. No new constitutions. No new frameworks.

---

## Mission

AGI should become the best institutional research platform by mastering the questions institutional investors actually ask.

The objective is not to answer company questions. The objective is to **answer investment questions**.

Every benchmark should improve AGI's ability to think like an analyst.

---

## Curriculum structure

```text
10 Decision Domains
  ↓
100 Institutional Questions (universal)
  ↓
10 Anchor Companies
  ↓
1000 Editorial Benchmarks
  ↓
Continuous Improvement
```

---

## Decision domains

| # | Domain | Purpose | Editorial objective |
|---|--------|---------|---------------------|
| 1 | Idea Generation | Should this company deserve research? | Prioritize research |
| 2 | Business Understanding | Understand before valuation | Explain businesses clearly |
| 3 | Competitive Advantage | Determine durability | Structural thinking |
| 4 | Management Quality | Evaluate leadership | Separate business from management |
| 5 | Financial Quality | Assess durability | Explain financial quality |
| 6 | Valuation | Understand expectations | Expectations, not multiples |
| 7 | Investment Debate | What investors disagree about | Probabilistic thinking |
| 8 | Portfolio Construction | Think beyond one company | Allocation |
| 9 | Monitoring | Continuous research | Dynamic investing |
| 10 | Decision Review | Learning | Institutional memory |

10 questions per domain = **100 universal questions** (`IICQ_001`–`IICQ_100`).

---

## Anchor companies (Phase 1)

TCS, Infosys, HDFC Bank, ICICI Bank, Reliance Industries, Titan, Asian Paints, Bharti Airtel, Larsen & Toubro, Maruti Suzuki.

Every company answers the same 100 institutional questions → **1000 benchmarks** (`IIC_0001`–`IIC_1000`).

---

## Editorial workflow

```text
Question → Decision Domain → Playbook → Research Workflow → Knowledge Objects
  → Evidence → Response Planning → Institutional Writing → Editorial Review → Hall of Fame
```

---

## Scoring dimensions

- Clarity  
- Institutional Tone  
- Business Understanding  
- Investment Insight  
- Evidence Integration  
- Narrative Flow  
- Explanation Quality  
- Portfolio Relevance  
- Investor Usefulness  
- Forward Without Editing  
- Overall Editorial Score  

---

## Editorial principles

1. Never answer the literal question only — answer the underlying investment question.  
2. Never explain facts without implications.  
3. Never present valuation without expectations.  
4. Never discuss risk without monitoring.  
5. Never conclude without uncertainty.  
6. Never summarize without teaching.  

Encoded as append-only rules ER-070 through ER-075.

---

## Hall of Fame

The **100 universal questions on TCS** (`IIC_0001`–`IIC_0100`) form the editorial gold standard set.

Re-run after every writing-layer change. Keep new version only if objectively better.

---

## Weekly editorial process (recommended)

Stop writing prompts. Start building a real editorial process:

1. Run **100 benchmark questions**  
2. Read every answer manually  
3. Improve only the weakest responses  
4. Add **1–3 editorial rules**  
5. Re-run Hall of Fame  
6. Repeat  

No architecture changes. Only editorial refinement.

---

## Success metric

AGI succeeds when institutional investors say:

> "This is how I would analyse the business."

rather than:

> "This is a good AI summary."

The curriculum is complete when AGI consistently demonstrates institutional thinking across all major investment decisions, regardless of company or sector.

---

## Implementation

| Package | Role |
|---------|------|
| `institutional_investor_curriculum/` | Domains, universal questions, 1000 benchmarks |
| `institutional_writing_benchmark/` | Registry + Hall of Fame |
| `editorial_excellence/` | Scorecard, rules, review workspace |

```python
from institutional_investor_curriculum import list_domains, list_benchmarks, editorial_process
from institutional_writing_benchmark import get_benchmark, hall_of_fame_ids
```

---

## Final principle

The objective is not to memorise companies. The objective is to **master institutional investing**.
