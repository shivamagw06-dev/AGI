# FSE-02.2 — End-to-End Production Verification

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Verification — observability milestone |
| **Owner** | AGIB Intelligence Platform |
| **Workstream** | FSE-02.2 |
| **Depends on** | FSE-00 Orchestrator (+ DLQ) · FSE-02 Collection · FSE-04…07 engines |
| **Package** | `intelligence-engine/financial_statements_engine/verification/` |
| **Frozen surfaces** | Parser · VFQE · Warehouse · DME · HD dual-write · Decision Engine |

> **Intent:** Prove that a real filing moves through the complete FSE pipeline automatically, with timed stages, immutable reports, provenance, SLA metrics, and verified DLQ / replay behaviour. **No architectural expansion. No business-logic changes.**

---

# 1. Mission

Demonstrate operational confidence in:

```text
Collectors → FSE-02 ingest() → Raw Evidence Store → evidence.stored
        → Pipeline Orchestrator
        → PARSE → VALIDATE → WAREHOUSE → DME
```

HD dual-write remains enabled. Consumers are not migrated.

---

# 2. Verification universe

Default companies (configurable via `FSE_VERIFY_UNIVERSE`):

`TCS` · `RELIANCE` · `HDFCBANK` · `INFY` · `ICICIBANK`

---

# 3. Pipeline verification checklist

For every workflow verify and time:

| Stage | Recorded fields |
| --- | --- |
| Raw Evidence Stored | start · finish · duration · status · retries |
| Workflow Created | identity + timestamps |
| Parse Started / Completed | start · finish · duration · status · retries |
| Validation Started / Completed | start · finish · duration · status · retries |
| Warehouse Published | start · finish · duration · status · retries |
| Derived Metrics Completed | start · finish · duration · status · retries |

---

# 4. Workflow report

Immutable JSON under `FSE_STORE_ROOT/verification/reports/`:

* `workflow_id` · company · filing · period · source · document_hash
* all stage timestamps · overall duration · final status
* retry history · DLQ status

---

# 5. Provenance

Operator lineage page:

```text
Workflow → Raw Evidence → Parse Manifest → Coverage Matrix
        → Validation Report → Warehouse Version → Derived Metrics Version
```

---

# 6. Mission Control dashboard

Verified companies · successful / failed / DLQ workflows · average & P95 duration · average parse / validation / publish / DME time · throughput · success rate.

---

# 7. Pipeline SLA

Queue depth · oldest queued · average / P95 workflow duration · retry rate · DLQ rate · workflow success % · stage success %.

---

# 8. Failure & idempotency

* Intentional stage failures → automatic retry → retry budget → `DEAD_LETTER` → manual replay → recovery
* Identical evidence replay → no duplicate raw evidence / workflow / warehouse / DME

---

# 9. Surfaces

| CLI | REST |
| --- | --- |
| `--verify-dashboard` | `GET /v1/financial-statements/verification/dashboard` |
| `--verify-workflow [ID]` | `GET …/verification/workflows` · `…/workflows/{id}` |
| `--verify-company TCS` | `POST …/verification/run/{company}` |
| `--workflow-report [ID]` | (embedded in workflow detail) |
| `--workflow-provenance [ID]` | `GET …/verification/provenance/{workflow_id}` |

---

# 10. Operator runbook

1. Run `--verify-company TCS` (or Mission Control `POST …/run/TCS`).
2. Confirm checklist all green and report persisted.
3. Open `--workflow-provenance <id>` for lineage.
4. Monitor `--verify-dashboard` for SLA / DLQ.
5. On DLQ: inspect error → `--orch-replay ID` (or verification recovery) → confirm `COMPLETED`.

## Recovery procedure

1. List DLQ (`--orch-dlq` / dashboard).
2. Diagnose failing stage from report.
3. Fix upstream evidence if needed (do **not** edit warehouse facts by hand).
4. `replay` from failing stage (resets retry budget).
5. Re-verify company; confirm provenance versions advanced or idempotent skips.

---

# 11. Success criteria

* Real filing traverses complete pipeline automatically
* Every stage timed and recorded
* Workflow reports generated
* Provenance inspectable
* SLA metrics available
* DLQ recovery verified
* Replay / idempotency verified
* No existing APIs or consumers broken
* HD dual-write remains enabled
