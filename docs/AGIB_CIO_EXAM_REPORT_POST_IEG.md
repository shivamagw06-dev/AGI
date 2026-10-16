# AGIB CIO Regression Exam Report — Post A+B+C+D+IAP+IEG

**Examiner role:** Independent Chief Investment Officer (certification board)  
**Candidate:** AGIB Ask Pipeline with Tracks A–D + IAP + **Institutional Evidence Graph (IEG)**  
**Date:** 2026-07-28  
**Questions:** Exact same 25 prompts as prior frozen exams  
**Execution path:** Intent → Evidence → Assembly → Framework → Playbook → **Evidence Graph** → Reasoning → ICE → UiService  
**Method constraint:** Measurement only after Sprint 2.1 soft-wire.

---

## Verdict

### Overall score: **7.82 / 10**

| Version | CIO Score | Δ vs prior |
|---------|----------:|----------:|
| Baseline | 3.66 | — |
| A+B+C+D | 6.26 | +2.60 vs base |
| +IAP | 7.54 | +1.28 |
| **+IEG** | **7.82** | **+0.28** |

### Certification: **PARTIALLY READY** (relationship layer working)

Target for Evidence Graph sprint was **~7.9**. Result **7.82** is within band.

**Not PRODUCTION READY.** Remaining drag: Track C sector collisions, thin live KF packs, abstract questions without entity seeds.

### Score distribution

| Verdict | Count |
|---------|------:|
| PARTIAL+ | 20 |
| PARTIAL | 5 |
| WEAK | **0** |

### Improvement vs post-IAP

| | Count |
|--|------:|
| Improved | 14 |
| No Change | 11 |
| Regressed | 0 |

---

## Executive finding

| Layer | Post IAP | Post IEG |
|-------|----------|----------|
| Procedures / checklists | Present | Retained |
| Isolated evidence facts | Thin | **Relationships + domain trees** |
| Multi-entity compare | Weak | **Strong (Q1/Q2/Q14)** |
| Replay depth (Q24) | Hygiene only | **Historical event nodes + PIT filter** |
| Cross-industry transmission | Playbook-only | **Oil/steel/rate graphs** |

IEG does what the Phase 2 brief asked: analysts retrieve **relationships**, not bags of facts.

---

## Scorecard

### Overall

| | A+B+C+D | +IAP | **+IEG** | Δ vs IAP |
|--|-------:|-----:|-------:|---------:|
| Overall | 6.26 | 7.54 | **7.82** | **+0.28** |

### Category

| Category | +IAP | +IEG | Δ |
|----------|-----:|-----:|--:|
| Company | 8.0 | 8.22 | +0.22 |
| Industry | 7.0 | 7.36 | +0.36 |
| Macro | 6.7 | 7.08 | +0.38 |
| Cross | 8.1 | 8.16 | +0.06 |
| Documents | 8.17 | 8.17 | 0.00 |
| Replay | 6.5 | **8.0** | **+1.5** |
| Institutional | 8.5 | 8.8 | +0.30 |

### Q24 (primary IEG target)

| | Score | Notes |
|--|------:|-------|
| Post IAP | 6.5 | as_of hygiene; empty IERE |
| **Post IEG** | **8.0** | 51 nodes · 33% domains · historical events bound · future AI nodes excluded · ICE `evidence_graph_visible` |

---

## Telemetry highlights

- Evidence graph visible in ICE: **25/25**
- Avg IEG nodes / question: **~40**
- Multi-entity graphs: Q1 (HDFC+INFY), Q2 (INFY/TCS/WIPRO), Q14 (INFY/INDIGO/MARUTI)
- Concept industry graphs: cement, steel, oil, hospitals, banks/NBFC/RE

---

## What still limits 8.2+

1. **Institutional Memory** (Sprint 2.2) — dynamic thesis history vs seed timelines  
2. **Track C sector collisions** — Q8/Q11 still incomplete  
3. **Live/KF historical packs** — Q24 still seed-assisted, not full IERE history  
4. **Judgement engine** — still summarises under correct structure  

---

## Recommendation

Ship IEG. Next sprint: **Institutional Memory** (target ~8.2), building on this graph rather than more agents.

Artifacts: `/opt/cursor/artifacts/cio-exam-ieg/`
