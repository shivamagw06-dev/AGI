# Phase 9 — Sprint 9.4: Institutional Probability & Confidence Intelligence (IPCI)

**Status:** Implemented in `intelligence-engine/institutional_probability_confidence/`  
**Version:** 0.1.0  
**Depends on:** Sprint 9.2 ISI Scenario Reports (and IFI bundles upstream)  
**Out of scope:** Forecast Validation & Learning (9.5), trading recommendations

---

## Core distinction

| Concept | Question |
|---|---|
| **Probability** | How likely is this scenario? |
| **Confidence** | How certain are we about our assessment? |

These are **independent**. A low-probability Bull case can still have high confidence in the quality of the evidence.

---

## Architecture

```text
ISI Bull / Base / Bear
        │
        ▼
IPCI (evidence scoring → probability + confidence)
        │
        ▼
Forecast Assessment → Investment Office
```

No live Yahoo / NSE calls. No guessing.

---

## Rules

- Bull + Base + Bear probabilities **always = 100%**
- Confidence computed from evidence quality, historical coverage, analogues, freshness, completeness, contradictions, trigger uncertainty, research quality
- Missing evidence is explicit and reduces confidence, not a blocker
- No BUY / SELL / target prices

---

## APIs

```text
GET  /v1/probability/company/{ticker}
GET  /v1/probability/sector/{sector}
GET  /v1/confidence/company/{ticker}
GET  /v1/forecast/assessment/{ticker}
POST /v1/forecast/assessment
GET  /v1/probability/dashboard
```

---

## Traces

`probability_calculation` · `confidence_calculation` · `evidence_scoring` · `forecast_assessment`

---

## Phase 9 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 9.1 | IFI | Prepare |
| ✅ 9.2 | ISI | Scenarios |
| ✅ 9.3 | CTI | Catalysts / triggers (soft-consumed) |
| ✅ 9.4 | IPCI | This sprint |
| ✅ 9.5 | FVL | Validate vs outcomes & learn — see `PHASE9_SPRINT_9_5_FVL.md` |
