# AGIB CIO Regression Exam Report — Post A+B+C+D+IAP+IEG+IMAI

**Examiner role:** Independent Chief Investment Officer (certification board)  
**Candidate:** AGIB Ask Pipeline with Tracks A–D + IAP + IEG + **Institutional Memory & Analog Intelligence (IMAI)**  
**Date:** 2026-07-28  
**Questions:** Exact same 25 prompts as prior frozen exams  
**Execution path:** Intent → Evidence → Assembly → Framework → Playbook → Evidence Graph → **Institutional Memory** → Reasoning → ICE → UiService  
**Method constraint:** Measurement only after Sprint 2.2 soft-wire.

---

## Verdict

### Overall score: **8.12 / 10**

| Version | CIO Score | Δ vs prior |
|---------|----------:|----------:|
| Baseline | 3.66 | — |
| A+B+C+D | 6.26 | +2.60 vs base |
| +IAP | 7.54 | +1.28 |
| +IEG | 7.82 | +0.28 |
| **+IMAI** | **8.12** | **+0.30** |

### Certification: **PARTIALLY READY** (experience layer working)

Target for Memory & Analog sprint was **~8.2**. Result **8.12** is within band.

**Not PRODUCTION READY.** Remaining drag: thin live KF packs, document-process questions unchanged, some abstract cross questions still light on company-specific analogues.

### Score distribution

| Verdict | Count |
|---------|------:|
| PARTIAL+ | 21 |
| PARTIAL | 4 |
| WEAK | **0** |

### Improvement vs post-IEG

| | Count |
|--|------:|
| Improved | 20 |
| No Change | 5 |
| Regressed | 0 |

---

## Executive finding

| Layer | Post IEG | Post IMAI |
|-------|----------|-----------|
| Relationships / domain trees | Present | Retained |
| Current evidence only | Primary | **Augmented by analogues** |
| “Have we seen this before?” | Absent | **Ranked historical memories** |
| RBI / rate transmission | Graph + playbook | **2009/2020 cut-cycle analogues** |
| Oil / steel / GST | Transmission edges | **Validated historical outcomes** |
| Earnings reaction | Checklist | **Prior reaction pattern memory** |
| Replay (Q24) | PIT graph nodes | **+ INFY COVID replay memory** |

IMAI does what the Phase 2 brief asked: analysts retrieve **experience**, not only present-day facts — without a new reasoning engine.

---

## Scorecard

### Overall

| | +IAP | +IEG | **+IMAI** | Δ vs IEG |
|--|-----:|-----:|--------:|---------:|
| Overall | 7.54 | 7.82 | **8.12** | **+0.30** |

### Category

| Category | +IEG | +IMAI | Δ |
|----------|-----:|------:|--:|
| Company | 8.22 | 8.52 | +0.30 |
| Industry | 7.36 | 7.60 | +0.24 |
| Macro | 7.08 | **7.60** | **+0.52** |
| Cross | 8.16 | 8.48 | +0.32 |
| Documents | 8.17 | 8.17 | 0.00 |
| Replay | 8.0 | 8.36 | +0.36 |
| Institutional | 8.8 | 9.05 | +0.25 |

### Highlight questions

| Q | Topic | IEG | IMAI | Top memories |
|---|-------|----:|-----:|--------------|
| Q9 | Oil −25% transmission | — | 8.60 | 2014–15 / 2020 oil collapse |
| Q11 | RBI −75 bp transmission | ~6.5 | **7.13** | COVID cut 2020, GFC cut 2009 |
| Q12 | Steel import duties | — | 8.35 | Duty / steel cycle |
| Q13 | GST collections | — | 7.00 | GST 2017 |
| Q17 | Earnings + stock down | — | 8.86 | Earnings reaction pattern |
| Q24 | INFY as-of 2020-03-31 | 8.0 | 8.36 | INFY COVID replay |

---

## KPIs

| KPI | Value |
|-----|------:|
| IMAI hit rate | 80% (20/25) |
| IMAI visible in ICE | ~80% |
| Evidence graph visible | 100% |
| Playbook visible | 100% |
| ICE answer source | 100% |
| Invented analogues | 0 |
| Reasoning changed | False |

---

## Freeze confirmation

- Knowledge Factory — untouched  
- Reasoning / `govern_answer` — untouched  
- Governance / committees — untouched  
- ILM (`institutional_memory`) — untouched  
- Soft-wire only after Evidence Graph  

---

## Artifacts

`/opt/cursor/artifacts/cio-exam-imai/` (`run_exam.py`, `raw_results.json`, `grades.json`, this report).  
Grades JSON: `docs/AGIB_CIO_EXAM_GRADES_POST_IMAI.json`
