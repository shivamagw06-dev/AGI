# AGIB Phase 3 — Sprint 3.2

## Root Cause Intelligence (RCI)

**Module:** `RCI`  
**Package:** `intelligence-engine/root_cause_intelligence/`  
**Version:** `root-cause-intelligence-v1.0.0`

### Why

IEL showed the weakness:

* 88.2% institutional pass rate
* Top: **framework mismatch** (proxy 75.3%)
* Second: **intent mismatch**

RCI turns “question failed” into clustered, patchable engineering work.

### Failure object

Every failed question becomes a structured record with expected vs actual intent/framework/playbook, evidence present/missing, reasoning path, communication, severity, root cause, confidence, and cluster id.

### Clustering

```text
root_cause × sector × framework_family × category × playbook_family
```

Fix clusters (e.g. 42 questions / framework mismatch / banks / Residual Income), not Q147.

### Engineering loop

```text
Git Commit → 1,025 Questions → Judges → RCI → Top 10 Clusters → Recommended PR → Engineer → Benchmark Again
```

### Soft-wire

IEL `run_benchmark` attaches `root_cause_intelligence` on every suite run.  
RCI **does not** patch selectors (that is Sprint 3.3).

### API

`/v1/root-cause-intelligence/{health,dashboard,nightly,analyze,history,report}`

### Next

Sprint **3.3 Framework Optimisation** — apply the top RCI-recommended patches and re-measure IEL.
