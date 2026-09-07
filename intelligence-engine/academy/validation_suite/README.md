# Academy Validation Suite V1

**Architecture status:** v1.0.1 LOCKED  
**Question:** Can the intelligence use what it learned to reason like an institutional analyst?  
**Not the question:** Did it ingest the book?

Soft programme on Academy Books V3. No engine / CID / analyst / UI redesign.

## Levels

| Level | Name | Pass focus |
|------:|------|------------|
| 1 | Concept Recall | Define, why it matters, when / when not — no book quotes |
| 2 | Framework Application | Apply to a real company with evidence + conclusion |
| 3 | Cross-book Synthesis | Integrate multiple authors into one institutional view |
| 4 | Case Transfer | Right analogue, similarities/differences, lessons |
| 5 | Counter-example Reasoning | Exceptions; concepts are not universal |
| 6 | Analyst-specific Exams | Business / Financial / Valuation domain tests |
| 7 | Memory Test | What changed since last review |
| 8 | Decision Test | Business → Financials → Valuation → Risks → Committee |

## APIs

- `GET /v1/academy/validation/health`
- `GET /v1/academy/validation/dashboard`
- `GET /v1/academy/validation/exams`
- `POST /v1/academy/validation/run` — full suite or `{levels:[1,3]}`
- `POST /v1/academy/validation/exam/{exam_id}`
- `GET /v1/academy/validation/quality-gates`

## Flag

`ACADEMY_VALIDATION_SUITE` / settings `academy_validation_suite`
