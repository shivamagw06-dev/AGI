# AGI Question Understanding Engine (QUE) v1.0

**Document type:** Institutional Research Specification  
**Layer:** Institutional Research Engine (IRE)  
**Status:** Core Runtime  
**Architecture:** Frozen — deterministic first stage  

---

## Purpose

Teach AGI to understand the meaning behind investor questions **before** performing research.

This is **not** an LLM prompt. This is the first deterministic stage of the research pipeline.

Every investment question has two layers:

1. The words the investor typed  
2. The investment decision the investor is trying to make  

**AGI must answer Layer 2, not Layer 1.**

---

## Mission

Institutional investors rarely ask exactly what they want to know. AGI exists to answer the **real question**.

| User asks | Literal | Real question |
|-----------|---------|---------------|
| Should I buy TCS? | Purchase decision | Should I allocate capital here vs another opportunity? |
| Why is Titan expensive? | Explain valuation | What expectations are embedded and are they justified? |
| Compare Infosys and TCS | Peer comparison | If I only invest in one, which differences matter? |

---

## Pipeline position

```text
User Question
  ↓
Question Understanding Engine (QUE)  ← FIRST
  ↓
Research Objective
  ↓
Research Workflow → Knowledge Objects → Evidence
  ↓
Response Planning → Institutional Writing → Editorial Review
  ↓
Final Response
```

If AGI misunderstands the question, everything downstream is wasted.

---

## 10-step QUE pipeline

1. **Literal question** — capture exactly what was asked  
2. **Underlying investor meaning** — what the investor is trying to accomplish  
3. **Decision type** — one primary decision (Capital Allocation, Research Priority, etc.)  
4. **Research objective** — what successful research should accomplish  
5. **Primary investment question** — committee-ready rewrite  
6. **Required information** — minimum categories needed  
7. **Irrelevant information** — what to ignore  
8. **Response objective** — Teach, Explain, Evaluate, Compare, etc.  
9. **Expected deliverable** — what the user should leave with  
10. **Success test** — can AGI state what decision the investor is trying to make?  

---

## Question understanding object

```json
{
  "literal_question": "...",
  "investor_meaning": "...",
  "decision_type": "...",
  "research_objective": "...",
  "primary_investment_question": "...",
  "required_information": [],
  "irrelevant_information": [],
  "response_objective": "...",
  "expected_deliverable": "...",
  "confidence": 0
}
```

Passed into every downstream engine via `out["question_understanding"]`.

---

## Decision types

Capital Allocation, Research Priority, Business Understanding, Valuation Assessment, Peer Selection, Portfolio Construction, Risk Assessment, Monitoring, Thesis Validation, Earnings Review, Macro Impact, Sector Allocation, Idea Generation, Education, Explainability, Unknown

---

## Question taxonomy

**500 labeled institutional questions** (`QT_0001`–`QT_0500`) in `question_understanding_engine/taxonomy.py`:

- Spec acceptance exemplars  
- Institutional Investor Curriculum templates (IIC-backed)  
- Common investor phrasing variants  

Each entry stores: literal question, underlying meaning, decision type, research objective, expected deliverable, response structure, editorial notes.

---

## Quality gates

QUE **fails** if any required field is missing:

- Decision type  
- Research objective  
- Underlying meaning  
- Response objective  
- Expected deliverable  
- Primary investment question  

---

## Acceptance tests

| Question | Decision | Research goal |
|----------|----------|---------------|
| Should I buy TCS? | Capital Allocation | Expected return vs risk |
| Does TCS deserve research? | Research Priority | Could more work change conclusions? |
| Compare Infosys and TCS | Peer Selection | Investment-relevant differences |

---

## Implementation

| Package | Role |
|---------|------|
| `question_understanding_engine/` | Resolver, taxonomy, validation, production |
| `answer_construction/production.py` | Wires QUE **first** in `package_for_ask_agi()` |

```python
from question_understanding_engine import apply_question_understanding_engine, understand_question
```

---

## Success metric

> "Yes, that is exactly what I wanted to know." — not — "That answered what I asked."

---

## Final principle

> Questions are language. Meaning is intent. Intent creates decisions.  
> Decisions determine research. Research produces judgment.

Every answer begins by understanding the investor — not the sentence.
