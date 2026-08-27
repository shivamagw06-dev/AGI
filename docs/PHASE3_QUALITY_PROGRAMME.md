# AGI Phase 3 — Quality Programme Roadmap

**Company:** AGI

Operating rule: **no features because they sound useful**.  
Every sprint starts with a measured weakness and ends with a measurable improvement.

## Status

| Phase | Focus | Status |
|-------|-------|--------|
| Architecture | Platform structure | ✓ |
| Knowledge | Knowledge Factory domains | ✓ |
| Evidence | IERE + Evidence Graph | ✓ |
| Communication | ICE + Playbooks + Memory | ✓ |
| **Quality Engineering** | Evaluation → temporal integrity | **Baseline frozen** |

CIO frozen exam (post-IMAI): **8.12 / 10**  
**AGI v3.5 engineering baseline:** **FROZEN / CERTIFIED** (post-TIRC)

## Sprint sequence

| Sprint | Capability | Exit metric |
|--------|------------|-------------|
| **3.1 IEL** ✅ | Institutional Evaluation Lab | 1000+ Q suite + nightly judge + dashboard |
| **3.2 RCI** ✅ | Root Cause Intelligence | Top-10 clusters + recommended PRs |
| **3.3 FO** ✅ | Framework Optimisation + Patch Intelligence | Framework accuracy ≥96% (target 98%) |
| **3.4 IO** ✅ | Intent Optimisation | Intent accuracy ≥99% (**100.0%**; IEL **98.4%**) |
| **Release Cert #234** ⛔ | Baseline freeze attempt | NOT CERTIFIED (leakage/replay) |
| **3.5 TIRC** ✅ | Temporal Integrity & Replay Certification | Future leakage **0**; replay **100%** |
| **Release Cert (post-TIRC)** ✅ | Baseline freeze | **CERTIFIED** — IEL **99.9%** |
| 4.1 | Evidence Weighting (IEW) — FROZEN v1.0.0 | Phase 4 Institutional Judgment |
| 4.2 | Hypothesis Generation (IHG) — FROZEN v1.0.0 | Phase 4 Institutional Judgment |
| 4.3 | Hypothesis Evaluation (IHE) — next | Phase 4 Institutional Judgment |
| 4.4–4.5 | Committee Reasoning / Confidence Calibration | Phase 4 Institutional Judgment |

## Parallel production track

BSE → RBI → IR Parser → 7-Day Certification

## Stopping condition (not “all modules done”)

| Metric | Target | Frozen baseline (post-TIRC full) |
|--------|-------:|----------------------------------:|
| CIO benchmark | ≥9.0/10 | 8.12 examiner / CIO-25 IEL 100% |
| IEL 1,025-question pass rate | ≥95% | **99.9%** |
| Framework accuracy | ≥98% | 97.76% |
| Intent accuracy | ≥99% | 99.8% (inst. 1000 soft 100%) |
| Hallucinated evidence | 0 | **0** |
| Replay correctness | 100% | **100%** |
| Future leakage | 0 | **0** |
| Live collector certification | 100% | pending production track |

**Release certification (post-TIRC):** **CERTIFIED** — engineering baseline frozen.  
See `docs/AGIB_RELEASE_CERTIFICATION_v3_5.md`. Phase 4 analytical depth may begin on this foundation.

## Tool roles (when purchased)

| Tool | Role |
|------|------|
| Claude Code | Large implementation sprints |
| Cursor Ultra | Day-to-day coding |
| ChatGPT | Architecture / roadmap reviews |
| LangSmith | Nightly evaluation + experiment tracking |
| Firecrawl | Institutional document ingestion |
| Exa | Research discovery / evidence expansion |
