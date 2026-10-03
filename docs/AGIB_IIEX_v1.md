# AGI Institutional Intelligence Examination (IIEX) v1.0

**Purpose:** Validate AGIB’s reasoning, research quality, evidence usage and investment judgement as a **CIO Investment Committee Assessment** — not a university paper.

**Module code:** `IIEX` (avoids collision with Investment Intelligence Engine `app/iie`)

| Spec | Value |
| --- | --- |
| Question bank | Q1–Q31 (Sections A–J) |
| Raw marks bank | 600 |
| Normalized total | **500** |
| Pass mark | **450 / 500 (90%)** |
| Negative marks | None |
| Resources | AGIB Intelligence Platform only — no internet |
| Scoring | Deterministic structural coverage / evidence / integration / guardrails (no LLM grading) |

## Sections

| Section | Focus | Marks |
| --- | --- | ---: |
| A | Company Intelligence | 100 |
| B | Market Intelligence | 75 |
| C | Macro Intelligence | 75 |
| D | Sector Intelligence | 75 |
| E | IPO Intelligence | 40 |
| F | Relationship Intelligence | 40 |
| G | Historical Intelligence | 30 |
| H | Forecast Intelligence | 40 |
| I | Research Intelligence | 60 |
| J | CIO Investment Committee | 65 |

Raw section marks sum to **600**. The runner normalizes to **/500** for the official pass bar.

## Final evaluation dimensions (/500)

| Dimension | Marks |
| --- | ---: |
| Accuracy | 100 |
| Reasoning | 100 |
| Evidence | 50 |
| Historical Context | 50 |
| Relationships | 50 |
| Forecasting | 50 |
| Research Quality | 50 |
| Portfolio Thinking | 50 |
| Communication | 50 |

## Soft intelligence probes (AGIB-only)

Answers soft-wire (never hard-fail) into:

- Company catalog / IFI
- CMKTP · HMKIP · MKRI · HMKAI · MKFI
- MFI · SFI
- RIH

`providers_queried` is always `[]`. `internet_used` is always `False`.

## APIs

Prefix `/v1` (FastAPI router):

| Method | Path |
| --- | --- |
| GET | `/institutional-intelligence-examination/health` · `/iiex/health` |
| GET | `/institutional-intelligence-examination/dashboard` · `/iiex/dashboard` |
| GET | `/institutional-intelligence-examination/questions` · `/iiex/questions` |
| POST | `/institutional-intelligence-examination/run` · `/iiex/run` |
| GET | `/institutional-intelligence-examination/report` · `/iiex/report` |
| GET | `/institutional-intelligence-examination/grades` · `/iiex/grades` |
| GET | `/institutional-intelligence-examination/history` · `/iiex/history` |

`POST …/run` body (optional): `{ "question_ids": ["Q1", "Q30"] }`.

## How to run locally

```bash
cd /workspace/intelligence-engine
PYTHONPATH=. python -m pytest institutional_intelligence_examination/tests/test_iiex.py -q
PYTHONPATH=. python - <<'PY'
from institutional_intelligence_examination.production import run, report
out = run()
print(out["summary"]["normalized_500"], out["summary"]["certification"])
print(report()["markdown"][:400])
PY
```

Reports written by the exam runner:

- `docs/AGIB_IIEX_EXAM_REPORT_v1.md`
- `docs/AGIB_IIEX_EXAM_GRADES_v1.json`

## Mission Control

Soft board key: `institutional_intelligence_examination` on the institutional intelligence aggregate (never hard-fails the dashboard).

## Certification bands

| Normalized /500 | Band |
| --- | --- |
| ≥ 450 | **INSTITUTIONAL READY** |
| 375–449 | PARTIALLY READY |
| < 375 | NOT READY |

## Design north star

AGIB competes with institutional platforms only when it can integrate every intelligence module into coherent, evidence-backed investment committee work.
