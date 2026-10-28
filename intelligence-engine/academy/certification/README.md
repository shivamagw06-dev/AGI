# Academy Certification Suite (ACS) V1

**Architecture status:** v1.0.1 LOCKED  
**Metric:** Reasoning quality  
**Not the metric:** Book ingest / concept existence

Certifies whether AGI has actually **learned** — every analyst, framework, concept and release.

## Grading

| Score | Grade |
|------:|------|
| 95–100 | Institutional Excellence (A+) |
| 90–94 | Institutional Ready (A) |
| 85–89 | Professional (B+) |
| 80–84 | Competent (B) |
| 70–79 | Developing |
| 60–69 | Weak |
| <60 | Fail |

**Merge floor:** Overall Institutional IQ ≥ 80 (Competent).

## Levels 1–18

Concept recall → framework application → cross-book synthesis → case transfer → counter-examples → analyst certification → memory → decision chain → case history → pattern recognition → portfolio → prediction accuracy → research writer → CIO → stress tests → benchmark suite → knowledge coverage → overall institutional IQ.

## Analyst exam banks

| Analyst | Target |
|---------|-------:|
| Business | 50 |
| Financial | 50 |
| Valuation | 50 |
| Sector | 40 |
| Macro | 40 |
| Risk | 40 |
| Management | 30 |
| Ownership | 30 |

## APIs

- `GET /v1/academy/certification/health`
- `GET /v1/academy/certification/dashboard`
- `GET /v1/academy/certification/inventory`
- `POST /v1/academy/certification/run` — `{full?: bool, limit_per_analyst?: int}`
- `POST /v1/academy/certification/gate` — merge gate
- `GET /v1/academy/certification/quality-gates`
- `POST /v1/academy/certification/exam/{exam_id}`

## Flag

`academy_certification_suite` / `ACADEMY_CERTIFICATION_SUITE`

## No redesign

Engine, UI, provider, Company Analysis, Investment Committee, CIO, Research Writer — soft certification only.
