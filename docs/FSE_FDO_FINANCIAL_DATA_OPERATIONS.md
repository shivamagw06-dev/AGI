# FSE-FDO — Financial Data Operations (Phase 1)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Operations — additive observability & scheduling |
| **Workstream** | FSE-FDO Phase 1 |
| **Package** | `intelligence-engine/financial_statements_engine/fdo/` |
| **Depends on** | FSE-02 ingest · Orchestrator · ECD · Verification · Mission Control |
| **Frozen** | Collectors · Parser · VFQE · Warehouse · DME · Orchestrator · Verification · HD dual-write |

> **Intent:** Transition AGIB from a system that *can* process financial statements into a platform that continuously **operates and scales** acquisition. Success = coverage, freshness, throughput, reliability.

---

# 1. Mission

Grow the Raw Evidence Store using real filings through the **existing** pipeline only:

```text
Collector → FSE-02 ingest() → Raw Evidence → Orchestrator
  → Parse → Validate → Warehouse → DME
```

No manual CLI for the happy path. No engine redesign.

---

# 2. Capabilities

| Capability | Role |
| --- | --- |
| Coverage engine | Latest annual/quarterly · years of history · missing periods · expected next · coverage % |
| Company completeness | Per-period checklist (present / missing / expected / not_released) |
| Gap scheduler | Prioritise lowest coverage, missing latest, stale companies |
| Live ingestion metrics | Collected today/week · latency · filings/hour · companies/day |
| Source metrics | Availability · success/failure · fallback · last success/failure |
| Raw evidence growth | Files · storage · by type/company/year · growth/day |
| Alerts | Coverage drop · DLQ · download failures · source down · no new filings |
| Mission Control | FDO dashboard aggregating the above |

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--fdo-dashboard` | `GET /v1/financial-statements/fdo/dashboard` |
| `--fdo-coverage [universe]` | `GET /v1/financial-statements/coverage` |
| `--coverage-company TCS` | `GET /v1/financial-statements/coverage/{company}` |
| `--source-health` | `GET /v1/financial-statements/source-health` |
| `--fdo-schedule` · `--fdo-alerts` | `GET …/fdo/schedule` · `GET …/fdo/alerts` |

Note: existing `--coverage` / `--coverage-dashboard` remain FSE warehouse / parse-coverage surfaces; FDO uses `--fdo-*` and `--coverage-company`.

Coverage is **Raw Evidence–first** (FSE meta under the store). Set `FDO_INCLUDE_HD=1` only when intentionally unioning Historical Depth periods into coverage inventory.

---

# 4. Non-goals

Do not redesign collectors, parser, VFQE, warehouse, DME, orchestrator, or verification. No new financial calculations. No consumer migration. No HD retirement.
