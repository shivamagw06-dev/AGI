# Office SDK — Shared Application Contract

## Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — shared contract for application offices |
| **Package** | `intelligence-engine/office_sdk/` |
| **Consumers** | IO-01 · CIO-01 · (future PO / WO / SO / VO / ITO) |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Mission Control |

> Every application office speaks the same interface: request → orchestrate existing intelligence → response with provenance.

---

# 1. Why

IO-01 and CIO-01 each grew office-local block/report shapes. As Portfolio, Watchlist, Screening, and Valuation offices arrive, duplicated plumbing becomes the bottleneck.

The Office SDK defines **one contract** for composition:

```
IO-01  ──┐
CIO-01 ──┼──► OfficeRequest / OfficeResponse
PO-01  ──┘         │
                   ▼
            EvidenceBlock
            EvidenceReference
            ConfidenceSummary
            ProvenanceBundle
            OfficeMetadata
```

---

# 2. Domains

| Domain | Offices |
| --- | --- |
| **Research** | IO-01, CIO-01 |
| **Portfolio** | PO-01 (planned), WO-01, SO-01 |
| **Market** | Market / Macro / News (planned) |
| **Execution** | Alerts / Monitoring / Notification (planned) |
| **Knowledge** | Research Notes / Documents / Session Desk (planned) |

---

# 3. Guardrails (all offices)

- Never recalculate FIRE / FKB / Warehouse facts  
- Never invent evidence or conclusions  
- Never emit BUY / SELL  
- Every narrative block carries provenance  
- Orchestration / state management only  

---

# 4. Surfaces

| CLI | REST |
| --- | --- |
| `python -m office_sdk --catalog` | `GET /v1/office-sdk/catalog` |
| `python -m office_sdk --health` | `GET /v1/office-sdk/health` |
| `python -m office_sdk --domains` | `GET /v1/office-sdk/domains` |
