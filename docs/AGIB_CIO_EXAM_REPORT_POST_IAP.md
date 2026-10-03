# AGIB CIO Regression Exam Report — Post A+B+C+D+IAP

**Examiner role:** Independent Chief Investment Officer (certification board)  
**Candidate:** AGIB Ask Pipeline with Tracks A–D + **Institutional Analytical Playbooks (IAP)**  
**Date:** 2026-07-28  
**Questions:** Exact same 25 prompts as baseline / post-ABC / post-ABCD exams  
**Execution path:** Question → Intent → Evidence → Assembly → Framework → **Playbook → Checklist** → Reasoning → ICE → UiService  
**Method constraint:** No prompt changes. No scoring-methodology changes. No further AGIB capability changes after the exam run. Measurement only.

---

## Verdict

### Overall score: **7.54 / 10**

| Version | CIO Score | Δ vs prior |
|---------|----------:|----------:|
| Baseline | 3.66 | — |
| Track A+B+C | 4.34 | +0.68 |
| Track A+B+C+D | 6.26 | +1.92 |
| **A+B+C+D+IAP** | **7.54** | **+1.28** |

### Certification: **PARTIALLY READY** (strong procedure lift)

**Not PRODUCTION READY. Not fully INSTITUTIONAL GRADE.**

IAP solved the bottleneck the prior CIO report named: missing institutional checklists and multi-step analytical procedures. Weak-block **Q17–Q23** moved from **5.36 → 8.21**. Remaining drag is mostly Track C sector collisions (Q8/Q11), thin live/historical evidence (Q24), and incomplete multi-entity synthesis — not absent procedures.

Target band cited before the sprint (**7.8–8.2**) was not fully reached; the playbook layer is clearly working on the intended questions.

### Score distribution (current)

| Verdict | Count |
|---------|------:|
| PARTIAL+ | 18 |
| PARTIAL | 6 |
| WEAK | 1 |

### Improvement vs post-A+B+C+D

| | Count |
|--|------:|
| Improved | 23 |
| No Change | 2 |
| Regressed | 0 |

---

## Executive finding (strict)

| Layer | Post A+B+C+D | Post + IAP |
|-------|--------------|------------|
| Framework selection | Accurate, visible | Unchanged (still correct where sector detection works) |
| Communication | ICE 100%; generic 0% | Retained |
| Analytical checklists | Missing | **Present and rendered** |
| Multi-step procedures | Missing | **Present (arrow chains in Analysis)** |
| IC thought process | Thin | **IC initiate / package playbooks** |
| Document protocols (Q22) | Missing | **Annual Report playbook** |
| Q17 ≥10 reasons | Fail | **Pass (results-reaction checklist)** |
| Live / historical depth | Thin | Still thin (unchanged by design) |

---

## Final scorecard

### Overall

| | Baseline | A+B+C | A+B+C+D | **+IAP** | Δ vs ABCD |
|--|---------:|------:|-------:|-------:|----------:|
| Overall | 3.66 | 4.34 | 6.26 | **7.54** | **+1.28** |

### Category scores

| Category | A+B+C+D | +IAP | Δ |
|----------|-------:|-----:|--:|
| Company | 7.5 | 8.0 | +0.5 |
| Industry | 6.3 | 7.0 | +0.7 |
| Macro | 5.7 | 6.7 | +1.0 |
| Cross | 5.5 | 8.1 | **+2.6** |
| Documents | 5.67 | 8.17 | **+2.5** |
| Replay | 6.5 | 6.5 | 0.0 |
| Institutional | 8.0 | 8.5 | +0.5 |

### Weak-block focus (Q17–Q23)

| | Score |
|--|------:|
| Post A+B+C+D | 5.36 |
| Post IAP | **8.21** |
| Δ | **+2.85** |

---

## Playbook routing (exam telemetry)

| Q | Playbook | Checklist steps | Visible in ICE |
|--|--|--:|--|
| Q1 | Bank Valuation (P/B · RI) | 11 | Yes |
| Q5 | Bank Valuation (P/B · RI) | 11 | Yes |
| Q17 | Why Stock Moved After Results | 12 | Yes |
| Q18–Q19 | Premium Valuation | 12 | Yes |
| Q20 / Q25 | IC Initiate / Fresh Coverage | 10 | Yes |
| Q22–Q23 | Annual Report Review | 10 | Yes |

Playbook selected: **25/25**. Playbook visible in communication: **25/25**. ICE answer source: **25/25**. Generic/blocked summaries: **0%**.

---

## What IAP proved

1. **Reasoning guidance works without rewriting reasoning** — packs + ICE surface procedures; `govern_answer` unchanged.
2. **Q17–Q23 were procedure problems**, not data problems — scores moved materially with checklists alone.
3. **Remaining gaps are outside IAP** — Track C keyword sector collisions, empty 2020 IERE packs, Yahoo 404 noise, multi-entity synthesis depth.

---

## What still fails / limits score to <8.0

- **Q8** remains WEAK (bank overweight on FMCG/IT/PSU Banks matrix).
- **Q11** still incomplete six-sector rate-cut chain under bank-framework bias.
- **Q24** replay hygiene OK; substance still empty (`ranked_count=0`).
- Playbooks are **procedures**, not filled evidence — confidence bands remain Moderate where packs are thin.
- Aspirational **7.8–8.2** band needs the next evidence/historical-depth work, not more framework packages.

---

## Recommendation

Ship IAP. Do **not** jump into more reasoning-engine redesign next.

Next highest ROI after this exam:

1. Fix Track C sector collisions (Q8/Q11).
2. Historical depth / non-empty replay packs (Q24).
3. Only then consider reasoning-engine improvements if Q17–Q23 plateaus.

---

Artifacts: `/opt/cursor/artifacts/cio-exam-iap/` (`run_exam.py`, `raw_results.json`, `grades.json`, this report).
