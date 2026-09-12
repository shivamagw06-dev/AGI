# AGI v3.6 — Institutional Judgment Release

```text
COMPANY: AGI
RELEASE: AGI v3.6 Institutional Judgment Release
STATUS: PRODUCTION ARCHITECTURE FROZEN
DATE: 2026-07-28
BASELINE PRIOR: AGI v3.5 CERTIFIED (engineering baseline)
```

## Board verdict

```text
######################################################################
#
#  AGI v3.6 — INSTITUTIONAL JUDGMENT LAYER FROZEN
#
#  Phase 4 complete. Stop building analytical machinery.
#  Phase 5 consumes this stack — it does not modify it.
#
######################################################################
```

**Engineering baseline:** v3.5 remains the certified quality floor.  
**Judgment architecture:** v3.6 freezes the Institutional Judgment Layer on top of that floor.

---

## Certified modules

| Layer | Module | Version | Status |
|-------|--------|---------|--------|
| Foundation | Knowledge Factory | frozen | ✓ |
| Intelligence | Evidence Retrieval | frozen | ✓ |
| Intelligence | Evidence Graph | frozen | ✓ |
| Intelligence | Institutional Memory | frozen | ✓ |
| Judgment | Evidence Weighting (IEW) | `institutional-evidence-weighting-v1.0.0` | ✓ Frozen |
| Judgment | Hypothesis Generation (IHG) | `institutional-hypothesis-generation-v1.0.0` | ✓ Frozen |
| Judgment | Hypothesis Evaluation (IHE) | `institutional-hypothesis-evaluation-v1.0.0` | ✓ Frozen |
| Judgment | Committee Reasoning (ICR) | `institutional-committee-reasoning-v1.0.0` | ✓ Frozen |
| Judgment | Confidence Calibration (ICC) | `institutional-confidence-calibration-v1.0.0` | ✓ Frozen |
| Integrity | Replay Integrity / TIRC | frozen | ✓ |
| Quality | Institutional Evaluation Lab | frozen judges / CIO weights | ✓ |
| Quality | Root Cause Intelligence | frozen soft-wire | ✓ |
| Delivery | Existing Reasoning | frozen | ✓ |
| Delivery | Institutional Communication | frozen | ✓ |

---

## Frozen judgment pipeline

```text
Question
  → Intent Resolution
  → Evidence Retrieval
  → Evidence Graph
  → Institutional Memory
  → Institutional Evidence Weighting      (IEW)
  → Institutional Hypothesis Generation   (IHG)
  → Institutional Hypothesis Evaluation   (IHE)
  → Institutional Committee Reasoning     (ICR)
  → Institutional Confidence Calibration  (ICC)
  → Existing Reasoning
  → Institutional Communication
```

This is the **Institutional Judgment Layer**.

It teaches AGI how an investment committee deliberates.  
It does **not** yet make AGI behave like a CIO over time.

---

## Soft certification snapshot (at freeze)

| Metric | Value |
|--------|------:|
| IEL institutional_1000 pass % | **99.9** |
| IEL mean score | **90.05** |
| CIO-25 pass % | **100** |
| HQS mean (independent) | **95.85** |
| CQS mean (independent) | **95.89** |
| CFQS mean (independent) | **100.0** |
| Reasoning changed by Phase 4 soft-wires | **No** |
| Future leakage / replay (v3.5 floor) | **Held** |

Independent Phase 4 metrics (never in CIO `DIMENSION_WEIGHTS`):

* **HQS** — Hypothesis Quality Score  
* **CQS** — Committee Quality Score  
* **CFQS** — Confidence Quality Score  

---

## Freeze rules (mandatory)

1. **Do not modify** IEW / IHG / IHE / ICR / ICC profiles or engines for Phase 5 feature work.
2. **Do not** add further judgment layers (no “Sprint 4.6”).
3. **Do not** replace existing Reasoning or ICE internals to chase CIO points.
4. Phase 5 modules **consume** judgment outputs (committee report, confidence report, weighted evidence, hypotheses) as inputs to persistent investment objects.
5. Benchmark-chasing against frozen judgment profiles is forbidden.

---

## What v3.6 is — and is not

| v3.6 is | v3.6 is not |
|---------|-------------|
| A complete institutional judgment stack | A CIO operating system |
| Deterministic, replay-safe, explainable confidence | A portfolio book |
| Committee-style multi-case deliberation | A live monitoring loop |
| The stable foundation for Phase 5 | Permission to keep expanding analysis |

---

## Next programme

**Phase 5 — Institutional Investment Office**

Question shifts from:

> How does AGI think?

to:

> Given all this intelligence, how does AGI behave like a CIO over time?

First sprint: **5.1 Institutional Investment Thesis Engine (ITE)** — living investment theses, not chat answers.

See: `docs/PHASE5_ROADMAP.md`

---

## Version stamp

```text
AGI v3.6 Institutional Judgment Release

Status: Production Architecture Frozen
Judgment stack: IEW · IHG · IHE · ICR · ICC  (all v1.0.0)
Quality floor: AGI v3.5 Certified
Phase 5: may begin — must not mutate this freeze
```
