# AGIB IB-01 — Institutional Benchmark

**Workstream:** IB-01  
**Platform:** AGIB v1.0.0 GA (architecture frozen)  
**Role:** Competitive intelligence grade  
**Adds intelligence engines:** No

---

## Mission

Can AGIB produce institutional-grade research comparable to Bloomberg, Capital IQ, FactSet, AlphaSense, and sell-side research?

```text
PAT-01 proves:  "The software works."
IB-01 proves:   "The investment intelligence is competitive."
```

Those are completely different claims.

Distinct from **IBS-01** (permanent sector case corpus) — IB-01 is the 1000-point competitive scorecard.

---

## Scoring

| Section | Focus | Points |
| --- | --- | ---: |
| A | Company Research (20 cos · investment view) | 200 |
| B | Blind Comparison (debranded reports) | 200 |
| C | Hallucination Test | 100 |
| D | Speed (Ask / Workspace / Publication) | 100 |
| E | Portfolio Test | 100 |
| F | Explainability (lineage walk) | 100 |
| G | Analyst Productivity (Bloomberg vs AGIB) | 100 |
| H | Stress Reasoning | 100 |
| **Overall** | | **1000** |

**Pass ≥ 900 → Institutional Grade**

Harness estimates can meet the numeric threshold (**provisional**). External claims require `claim_safe=true` (recorded blind panel ≥3 + Bloomberg/AGIB productivity groups).

---

## Section B — Blind Comparison (most valuable)

1. Collect reports from Bloomberg Intelligence, Capital IQ, Morningstar, brokerage.  
2. Remove branding → Report A–D + AGIB.  
3. Ask experienced analysts: *Which report would you rather use?*  
4. Do not reveal which is AGIB.  
5. Record votes via `POST /v1/benchmark/ib/blind-vote`.

---

## Package

```text
intelligence-engine/institutional_grade_benchmark/
    runner.py
    report.py
    sections/     # A–H
    dashboards/   # Benchmark Center
    store.py      # panel votes / productivity
```

---

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python -m institutional_grade_benchmark
```

---

## APIs

| Method | Path |
| --- | --- |
| GET | `/v1/benchmark/ib/health` |
| POST | `/v1/benchmark/ib/run` |
| GET | `/v1/benchmark/ib/report` |
| GET/POST | `/v1/benchmark/ib/section/{section}` |
| POST | `/v1/benchmark/ib/blind-vote` |
| POST | `/v1/benchmark/ib/productivity` |
| POST | `/v1/benchmark/ib/manual-score` |
| GET | `/v1/benchmark/ib/diagnostics` |

Mission Control **Benchmark Center** shows overall score, grade, panel status, and section scorecard.

---

## Example output shape

```text
AGIB Benchmark

Company Research
193/200

Blind Review
183/200
…

Overall

951/1000

Institutional Grade
```

---

## Productivity case — Reliance investment note

A more valuable question than “Does it beat Bloomberg?”:

> Does AGIB make a professional analyst materially more productive?

**Artifacts**

* `docs/research_notes/RELIANCE_INVESTMENT_NOTE.md` — analyst-edited note  
* `docs/research_notes/RELIANCE_PRODUCTIVITY_CASE.md` — measured scorecard  
* `GET/POST /v1/benchmark/ib/cases/reliance-productivity`

| Metric | Reliance case |
| --- | ---: |
| Time to first draft | ~1.1 s |
| Factual corrections | 8 |
| Completeness (edited) | 78/100 |
| Blind reviewer quality | 72/100 |
| Buy-side PM review | **67/100** |
| Confidence | 0.45 |
| Sources cited | 5 (0 primary filings in-graph) |
| Publication gates | **FAIL** (scaffold only) |

**PM one-liner:** *Good first draft. Don't publish it yet.*

**Verdict:** AGIB does **not** replace the analyst and did **not** prove Bloomberg parity in this run — but it **did** compress first-draft scaffolding from hours to seconds when corrections are enforced.

### Publication gates (85+ bar)

`POST /v1/benchmark/ib/publication-gates` · `GET /v1/benchmark/ib/publication-gates/reliance`

Blocks publication until: thesis bullets · financials · segment economics · valuation · decision triggers · evidence links · contradiction check.
