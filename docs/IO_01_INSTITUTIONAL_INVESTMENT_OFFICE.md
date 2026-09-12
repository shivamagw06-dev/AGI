# IO-01 — Institutional Investment Office

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — orchestration / application layer |
| **Workstream** | IO-01 |
| **Package** | `intelligence-engine/investment_office/` (additive IRP layer) |
| **Consumes** | Warehouse · DME · FIRE-01…06 · FKB |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Mission Control · existing IO desk |

> Investment Office answers: *Given everything AGIB already knows, what evidence is relevant to this investment question?*

---

# 1. Mission

Orchestration layer. Assembles existing FIRE outputs into **Institutional Research Packages (IRP)**.

- Never replaces FIRE  
- Never recalculates, re-scores, or re-analyses  
- Never invents evidence or conclusions  
- No BUY / SELL / valuation / DCF / forecasts  

---

# 2. Package types

Financial Health · Business Quality · Management Review · Evidence Review · Execution Review · Capital Allocation · Cash Flow Review · Balance Sheet Review · Growth Review · Company Snapshot · Institutional Brief

---

# 3. Question routing (examples)

| Question | Modules |
| --- | --- |
| How strong is the balance sheet? | FIRE-02, FIRE-06 |
| What changed this year? | FIRE-01, FIRE-02 |
| Has management delivered? | FIRE-05 |
| Is management's strategy supported? | FIRE-03, FIRE-04 |
| Explain the company | Institutional Brief (FIRE-01…06) |

---

# 4. Surfaces

| CLI | REST |
| --- | --- |
| `--company TCS` | `GET /v1/investment-office/company/{ticker}` |
| `--question "…"` | `POST /v1/investment-office/query` |

Existing desk endpoints (`/dashboard`, `/quality-gates`, `/package`) remain unchanged.

---

# 5. Design principle

| Layer | Role |
| --- | --- |
| FSE | Facts |
| FKB | Knowledge |
| FIRE | Analysis |
| Investment Office | Workflow & presentation |
