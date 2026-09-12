# AGIB Phase 3 — Sprint 3.1

## Institutional Evaluation Lab (IEL)

**Module:** `IEL`  
**Package:** `intelligence-engine/institutional_evaluation_lab/`  
**Version:** `institutional-evaluation-lab-v1.0.0`

### Why this sprint

Architecture, knowledge, evidence, and communication are in place (CIO **8.12/10**).  
The next investment is **Quality Engineering** — every sprint must start with a measured weakness and end with a measurable improvement.

IEL replaces ad-hoc 25-question judgment with a professional evaluation pipeline.

### Package layout

```text
institutional_evaluation_lab/
  benchmarks/     # probe + runner
  judges/         # deterministic structural judges
  datasets/       # CIO-25 gold + 1000+ generator
  scoring/        # weighted dimension scores
  regression/     # baseline compare
  analytics/      # root-cause clusters (Sprint 3.2 seed)
  reports/        # markdown + baseline.json
  dashboards/     # Mission Control board
  tests/
```

### Question object

Every question stores: Question, Intent, Framework, Expected Evidence, Expected Playbook, Expected Confidence, Expected Reasoning, Ground Truth, Acceptable Alternatives, Difficulty, Sector, Version.

### Suites

| Suite | Size | Role |
|-------|-----:|------|
| `cio_frozen_25` | 25 | Gold regression (frozen CIO exam) |
| `institutional_1000` | ≥1000 | Nightly structural benchmark |
| `smoke` | ~20 | CI fast path |
| `all` | ≥1025 | Combined |

### Nightly pipeline

```text
GitHub Commit → 1000 Questions → AGIB soft probe → Judge → Score → Root Cause → Dashboard
```

Soft probe measures: Intent → Framework → Playbook → Evidence Graph → IMAI  
(Full ask mode available for sampled deep runs.)

### Quality Programme targets (north star)

| Metric | Target |
|--------|-------:|
| CIO benchmark | ≥9.0/10 |
| 1,000-question pass % | ≥90% |
| Replay accuracy | 100% |
| Framework selection | ≥98% |
| Unsupported claims | 0 |
| Hallucinated evidence | 0 |

### API

`/v1/institutional-evaluation-lab/{health,dashboard,catalog,run,nightly,history,question/{id}}`

### Freeze locks

Measurement only. No reasoning engine changes. No KF redesign. Deterministic judges (no LLM grading).

### Next sprints (roadmap locked)

- **3.2** Failure Intelligence (persist/cluster 5000 failures)
- **3.3** Hypothesis Engine
- **3.4** Evidence Weighting
- **3.5** Contradiction Engine
- **3.6** Investment Committee Simulator  
Parallel: BSE / RBI / IR Parser / 7-Day Certification
