# FSE-02.3 — Official Source Registry & Multi-Source Collection

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production Extension — additive to FSE-02 / FSE-02.1 |
| **Workstream** | FSE-02.3 |
| **Package** | `intelligence-engine/financial_statements_engine/collection/source_layer/` |
| **Depends on** | FSE-02 Collection · FSE-02.1 Canonical `ingest()` |
| **Frozen** | Parser · VFQE · Warehouse · DME · Orchestrator · HD dual-write · consumers |

> **Intent:** Extend the collection layer with a **Source Registry** and official adapters (MCA, NSE, BSE, Company IR). Every download still enters only through `FSE-02 ingest()`. No engine redesign.

---

# 1. Mission

```text
Official sources (MCA → NSE → BSE → IR)
        │
        ▼
Source adapters (discover / download / metadata / health)
        │
        ▼
Fallback engine (next healthy source on failure)
        │
        ▼
FSE-02 ingest()
        │
        ▼
Raw Evidence Store → evidence.stored → Orchestrator
```

Collectors never call Parser, Validation, Warehouse, or DME.

---

# 2. Source priority (registry-driven)

| Priority | Source ID | Adapter |
| --- | --- | --- |
| 1 | `mca_xbrl` | `source_layer.mca` |
| 2 | `nse_official` | `source_layer.nse` |
| 3 | `bse_official` | `source_layer.bse` |
| 4 | `company_ir` | `source_layer.investor_relations` |

The collector selects the highest-priority **enabled + healthy** source that supports the requested filing type. Future sources (SEBI, commercial) register the same way — no ingestion-logic rewrite.

---

# 3. Adapter interface

Each adapter exposes:

* `discover(ticker, **kwargs) -> list[discovery]`
* `download(discovery_row) -> {ok, bytes, ...}`
* `metadata(discovery_row) -> dict`
* `health() -> dict`

Adapters do not import Parser / Warehouse / DME.

---

# 4. Provenance (required on every raw object)

`company_id` · `company_name` · `source` · `filing_type` · `reporting_period` · `filing_date` · `document_hash` · `download_timestamp` · `original_filename` · `mime_type` · `source_url` · `source_priority` · `alternate_sources[]`

Duplicates: one canonical blob; all provenance sources recorded.

---

# 5. Configuration

| Env | Default |
| --- | --- |
| `ENABLE_MCA` | `true` |
| `ENABLE_NSE` | `true` |
| `ENABLE_BSE` | `true` |
| `ENABLE_IR` | `true` |
| `SOURCE_TIMEOUT` | `30` |
| `MAX_DOWNLOAD_RETRIES` | `3` |

---

# 6. Mission Control

`GET /v1/financial-statements/collection/source-coverage` · `--source-coverage`

Coverage by source / company / filing type / year · health · success % · latency · failures · fallback usage.

---

# 7. Non-goals

Do not modify Parser, VFQE, Warehouse, DME, Orchestrator, consumer contracts, HD migration, or financial calculations.
