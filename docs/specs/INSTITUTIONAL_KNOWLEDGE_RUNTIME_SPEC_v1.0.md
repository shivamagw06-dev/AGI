# AGI Institutional Knowledge Runtime (IKR) Specification v1.0

**Document type:** Engineering Specification  
**Layer:** Institutional Knowledge Layer  
**Status:** Core Runtime  

---

## Purpose

The **Institutional Knowledge Runtime (IKR)** is the execution layer that manages all institutional knowledge objects inside AGI.

IKR is **not** a database, intelligence engine, or LLM. It is the runtime that loads, validates, selects, versions, and updates institutional knowledge **during execution**.

Without IKR, AGI has information. With IKR, AGI has institutional knowledge.

---

## Mission

Every investment question answered by AGI must first pass through IKR.

The runtime determines:

- Which knowledge objects are required  
- Which assertions are relevant  
- Which evidence supports them  
- Which assertions are stale  
- Which assertions contradict one another  
- Which assertions require review  

The runtime provides **trusted institutional knowledge** to every downstream component.

---

## Position in architecture

```text
Evidence Sources
  ↓
Evidence Graph
  ↓
Institutional Knowledge Runtime (IKR)     ← this spec
  ↓
Institutional Knowledge Objects (IKO)     ← claim-centric storage model
  ↓
Research Workflows
  ↓
Playbooks
  ↓
Investment OS
  ↓
Response
```

---

## Core responsibilities

| Responsibility | Owner |
|----------------|-------|
| Knowledge loading | IKR |
| Assertion resolution | IKR |
| Evidence resolution | IKR (refs only; Evidence Graph stores raw evidence) |
| Dependency resolution | IKR |
| Knowledge validation | IKR |
| Version management | IKR |
| Monitoring status | IKR |
| Unknown detection | IKR |
| Contradiction resolution | IKR |
| Knowledge selection | IKR |

IKR **never** performs financial analysis. It manages knowledge.

---

## Knowledge objects

Runtime supports (extensible registry):

| Object type | Module | Status |
|-------------|--------|--------|
| Company IKO | `institutional_knowledge_object` | v1 implemented |
| Sector IKO | — | registered, not implemented |
| Macro IKO | — | registered, not implemented |
| Portfolio IKO | — | registered, not implemented |
| Management IKO | — | registered, not implemented |
| Theme IKO | — | registered, not implemented |
| Commodity IKO | — | registered, not implemented |
| Country IKO | — | registered, not implemented |

Future types register via `IKR_OBJECT_REGISTRY` without runtime rewrite.

---

## Assertion model

Institutional knowledge consists of **assertions** (IKO: claims).

```yaml
assertion_id: CLAIM_TCS_SWITCHING_COSTS_001
entity_id: TCS
entity_type: company
category: competitive_position
statement: TCS possesses durable switching costs with large enterprise clients.
status: SUPPORTED
confidence: 91
evidence_refs: [...]           # pointers into Evidence Graph
dependencies: [CLAIM_TCS_MARGINS_002]
monitoring: { trigger, status, last_checked }
version: 3
timestamp: 2026-08-05T00:00:00Z
author: evidence_pipeline
source: annual_report_2025
history: [...]                   # append-only
```

---

## Assertion states

| State | Meaning |
|-------|---------|
| `SUPPORTED` | Evidence-backed; actively maintained |
| `PARTIAL` | Directionally known; material gaps |
| `CONTRADICTED` | Conflicting evidence; requires resolution |
| `UNKNOWN` | Not yet researched |
| `UNDER_REVIEW` | Active reassessment |
| `STALE` | Evidence aged beyond threshold |
| `DEPRECATED` | Superseded; retained for audit |

Assertions never disappear. Status evolves.

---

## Runtime pipeline

Every execution follows:

```text
1. Load Knowledge Object
2. Load Assertions
3. Resolve Dependencies
4. Resolve Evidence
5. Resolve Contradictions
6. Evaluate Monitoring Rules
7. Calculate Assertion Confidence
8. Return Validated Assertions
```

Implementation: `institutional_knowledge_runtime/pipeline.py`

---

## Dependency engine

Assertions may depend on other assertions.

Example: **Pricing Power** depends on **Margins**, **Customer Retention**, **Market Share**.

If a dependency transitions to `CONTRADICTED` or `STALE`, dependent assertions automatically transition to `UNDER_REVIEW`.

---

## Assertion confidence (deterministic)

Components:

| Input | Weight |
|-------|--------|
| Evidence quality | 0.30 |
| Evidence freshness | 0.20 |
| Coverage completeness | 0.20 |
| Historical consistency | 0.15 |
| Contradiction penalty | 0.10 |
| Monitoring health | 0.05 |

Every score exposes: `formula`, `inputs`, `weights`, `result`.

Confidence represents **evidence reliability**, not expected return.

---

## Evidence resolution

IKR **never stores evidence**. Evidence remains in Evidence Graph.

Runtime loads per assertion:

- Supporting evidence refs  
- Contradicting evidence refs  
- Confidence, freshness, source quality (from graph pack when provided)  

---

## Monitoring

Assertions declare monitoring rules. If threshold fails → status transitions automatically.

Example:

```yaml
assertion: TCS possesses durable pricing power
monitoring:
  metrics: [operating_margin, client_retention, large_deal_wins]
  trigger: operating_margin < 22%
  status: healthy | breached | unknown
```

---

## Unknown management

Unknowns are first-class:

```yaml
unknown:
  assertion_id: CLAIM_TCS_PEER_VAL_003
  reason: Peer valuation evidence not yet collected
  priority: high
  required_evidence: [peer_multiples]
  expected_source: valuation_intelligence
  responsible_engine: valuation_intelligence
```

---

## Version management

Append-only. Updates never overwrite history.

```yaml
version_entry:
  assertion_id: CLAIM_TCS_VAL_004
  previous_version: 2
  current_version: 3
  evidence_added: [EV_PEER_Q2_2026]
  evidence_removed: []
  reason: Peer context completed
  timestamp: 2026-08-05T14:00:00Z
  source: workflow_completion
```

---

## Knowledge selection

When Ask or a workflow requests information, IKR returns:

- Relevant assertions  
- Linked evidence refs  
- Unknowns  
- Contradictions  

No downstream component searches storage directly.

---

## Public API

| Method | Purpose |
|--------|---------|
| `load_object(entity_type, entity_id, **kwargs)` | Load IKO + run pipeline |
| `select_assertions(pack, **kwargs)` | Select for Ask/workflow |
| `resolve_dependencies(assertions)` | Propagate dependency state |
| `validate_assertions(assertions)` | Validation gate |
| `calculate_confidence(assertion, evidence_pack)` | Deterministic score |
| `update_assertion(...)` | Approved writers only |
| `version_assertion(...)` | Append version entry |
| `list_unknowns(iko)` | First-class unknowns |
| `list_monitoring(iko)` | Active monitoring rules |
| `run_pipeline(iko, **kwargs)` | Full 8-step execution |

Implementation: `institutional_knowledge_runtime/production.py`

---

## Writers (approved)

| Writer | May update assertions |
|--------|----------------------|
| Evidence Pipeline | Yes |
| Workflow Completion | Yes |
| Decision Memory | Yes (version only) |
| Monitoring Engine | Yes (status/monitoring) |
| Manual Analyst Review | Yes |
| Investment OS | Yes (thesis assertions) |
| **LLM** | **Never** |

---

## Readers

Ask, Research Workflows, Playbooks, Investment OS, Forecast Engine, Monitoring Engine, Company Workspace, Portfolio Workspace.

---

## Validation

Runtime validates before returning assertions:

- Evidence exists for `SUPPORTED`  
- Confidence in range 0–100  
- Dependencies resolved  
- Status valid  
- Monitoring configured where required  
- Version current  
- Unknowns tracked  
- Contradictions linked  

---

## Acceptance tests

| Test | Pass |
|------|------|
| Assertion loaded | ✓ |
| Dependencies resolved | ✓ |
| Evidence linked | ✓ |
| Contradictions detected | ✓ |
| Monitoring evaluated | ✓ |
| Confidence calculated | ✓ |
| Version tracked | ✓ |
| Unknowns exposed | ✓ |
| Public API stable | ✓ |

---

## Non-goals

IKR does **not**:

- Generate prose  
- Perform valuation  
- Forecast earnings  
- Issue recommendations  
- Replace intelligence engines  
- Store raw evidence  

---

## Implementation map

| File | Role |
|------|------|
| `institutional_knowledge_runtime/schema.py` | States, pipeline, writers |
| `institutional_knowledge_runtime/store.py` | In-memory IKO cache |
| `institutional_knowledge_runtime/pipeline.py` | 8-step execution |
| `institutional_knowledge_runtime/confidence.py` | Deterministic scoring |
| `institutional_knowledge_runtime/dependencies.py` | Dependency propagation |
| `institutional_knowledge_runtime/evidence.py` | Evidence Graph bridge |
| `institutional_knowledge_runtime/monitoring.py` | Rule evaluation |
| `institutional_knowledge_runtime/production.py` | Public API |

---

## Success metric

Institutional knowledge behaves like **living operating memory**:

- Every response uses validated assertions  
- Every assertion has evidence (or is explicitly `UNKNOWN`)  
- Every assertion evolves automatically as evidence changes  

---

## What comes next (build, not spec)

1. **IKR persistent store** (replace in-memory)  
2. **Evidence Graph** — evidence → assertion edges  
3. **Decision Memory** — assertion versioning at scale  
4. **Company DNA population** — high-quality assertions for universe  
5. **Investment OS** — orchestrate over validated assertions  

*This is the last architectural specification. Next artifacts are build implementations.*
