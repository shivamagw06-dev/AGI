# CIO-01 — Comparative Intelligence Office

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — application layer (comparison only) |
| **Workstream** | CIO-01 |
| **Package** | `intelligence-engine/comparative_intelligence/` |
| **Consumes** | FIRE-01…06 · IO-01 IRP orchestration · Warehouse · DME · FKB |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · IO desk · Mission Control · peer_intelligence |

> Comparative Intelligence answers: *Given everything AGIB already knows about these companies, what evidence supports a side-by-side comparison?*

---

# 1. Mission

Cross-company orchestration. Assembles existing FIRE / IO outputs into an **Institutional Comparison Report (ICR)**.

- Never replaces FIRE or IO-01  
- Never recalculates, re-scores, or re-analyses  
- Never invents evidence or conclusions  
- No BUY / SELL / valuation / DCF / forecasts  
- Not FIRE-07  

---

# 2. Comparison dimensions

Business Quality · Growth · Margins · Cash Flow · Balance Sheet · Capital Allocation · Management Execution · Evidence Alignment · Financial Trends · Financial Relationships

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--compare TCS INFY` | `POST /v1/comparative-intelligence/compare` |
| `--question "Compare HDFCBANK and ICICIBANK"` | `POST /v1/comparative-intelligence/query` |
| `--health` | `GET /v1/comparative-intelligence/health` |

---

# 4. Design principle

| Layer | Role |
| --- | --- |
| FSE | Facts |
| FKB | Knowledge |
| FIRE | Analysis |
| IO-01 | Single-company research workflow |
| **CIO-01** | Cross-company comparison workflow |
