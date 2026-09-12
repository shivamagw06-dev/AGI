# AGI Question Understanding Engine v1.1 — Research Brief Generator

**Document type:** Institutional Research Specification  
**Layer:** Institutional Research Engine (IRE)  
**Status:** Core Runtime  
**Architecture:** Frozen — operating contract for entire research pipeline  

---

## Purpose

QUE v1.0 understood the question. **QUE v1.1 tells the rest of AGI how to answer it.**

QUE does **not** answer questions. It produces a **Research Brief** that every downstream system consumes.

---

## Pipeline

```text
User Question
  ↓
Question Understanding
  ↓
Research Brief (NEW)
  ↓
Research Workflow → Knowledge Objects → Evidence Graph
  ↓
Response Planning → Institutional Writing → Editorial Review
  ↓
Final Response
```

---

## Research Brief object

```json
{
  "literal_question": "",
  "investor_meaning": "",
  "decision_type": "",
  "research_objective": "",
  "primary_investment_question": "",
  "required_information": [],
  "optional_information": [],
  "irrelevant_information": [],
  "knowledge_gap": "",
  "top_research_questions": [],
  "response_promise": "",
  "response_objective": "",
  "expected_deliverable": "",
  "success_criteria": [],
  "confidence": 0
}
```

---

## v1.1 additions (steps 6–10)

| Step | Output |
|------|--------|
| 6. Information Need Resolver | Required, optional, irrelevant categories |
| 7. Investor Knowledge Gap | What the investor probably does not understand yet |
| 8. Top Research Questions | Three institutional questions that matter most |
| 9. Response Promise | What the answer will achieve before research begins |
| 10. Research Brief | Complete operating contract |

---

## Example

**Question:** Does Tata Consultancy Services deserve research today?

| Field | Value |
|-------|-------|
| Decision | Research Priority |
| Research goal | Determine whether additional analysis could materially improve the investment thesis |
| Top questions | What uncertainty remains? Could research change assumptions? Why allocate analyst time here? |
| Ignore | Price targets, technical analysis, historical dividend record |
| Response promise | Investor understands whether TCS deserves analyst attention and why |

---

## Downstream contract

`downstream_contract()` maps the brief to consumer-specific instructions:

- **Research Workflow** — `required_information`, top questions  
- **Knowledge retrieval** — prioritize / deprioritize categories  
- **Evidence Graph** — focus on top research questions  
- **Response Planner** — primary investment question, response promise, success criteria  
- **Editorial Review** — evaluate against success criteria  

---

## Success test

Every downstream engine can answer **"What am I trying to accomplish?"** without reading the original question.

---

## Implementation

| File | Role |
|------|------|
| `question_understanding_engine/research_brief.py` | Brief generator + downstream contract |
| `question_understanding_engine/production.py` | Emits `research_brief` on every query |
| `institutional_writing_constitution/response_planner.py` | Consumes brief for planning |
| `research_workflow_framework/production.py` | Consumes required information |

---

## Final principle

> People ask questions using language. Investors make decisions using understanding.  
> QUE transforms language into understanding **before** research begins.

AGI must never answer the sentence. AGI must answer the decision hidden inside the sentence.

After v1.1, stop writing specifications. Focus on making every downstream component consume the Research Brief — and on the quality of underlying knowledge.
