# Phase 3 — Continuously Learning Investment Office

Phase 2 gave AGIB institutional evidence. Phase 3 adds **incremental memory** and **relational reasoning**.

```text
Historical Data Lake
        │
        ▼
Knowledge Compiler → CompanyMemory vN
        │
 ┌──────┴──────┐
 ▼             ▼
Delta Engine   Knowledge Graph
 └──────┬──────┘
        ▼
 Composite Memory → CID → Decision Engine
```

## P3.1 Knowledge Delta Engine

- Incremental compile vs prior CompanyMemory (`knowledge_delta_engine`)
- Delta types: UNCHANGED / ADDED / UPDATED / REMOVED / SUPERSEDED / CORRECTED / CONFLICT
- Version chain + checksum + event ledger (never silent overwrite)
- Structured `memory_delta` + explainability traces
- Identical evidence → deterministic noop

APIs: `/v1/knowledge-delta-engine/*`

## P3.2 Investment Knowledge Graph

- Company / sector / institution / theme / macro / event nodes and edges
- Soft-consumes locked IKG; does not mutate Decision Engine
- Composite retrieval: CompanyMemory + Graph + Latest Delta + CID

APIs: `/v1/investment-knowledge-graph/*`

## Governance

- Decision Engine still consumes **CID only**
- No BUY/SELL from delta or graph engines
- Constitution / gate thresholds unchanged
