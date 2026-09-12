# CW-01 — Company Workspace

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — Company Domain (primary UX) |
| **Workstream** | CW-01 |
| **Package** | `intelligence-engine/company_workspace/` |
| **Consumes** | IO-01 · CIO-01 · FIRE-01…06 · Office SDK · PEB-01 · WO-01 · PO-01 |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Office SDK · PEB · IO/CIO/PO/WO |

> Company Workspace answers: *Everything AGI currently knows about this company, in one place.*

---

# 1. Mission

Institutional users think in companies — not modules.

- **Not** an intelligence engine  
- **Not** an Office  
- Primary user experience for analysing a company  
- Orchestrates existing intelligence only  
- Never runs FIRE, never rescores, never emits BUY/SELL  

**Design principle**

| Layer | Owns |
| --- | --- |
| FSE | Facts |
| FKB | Knowledge |
| FIRE | Intelligence |
| Offices | Workflows |
| **Company Workspace** | **User experience** |

---

# 2. Workspace sections

Overview · Company Profile · Business Quality (FIRE-06) · Financial Trends (FIRE-01) · Financial Relationships (FIRE-02) · Management Execution (FIRE-05) · Evidence Alignment (FIRE-04) · Business Strategy (FIRE-03) · Historical Timeline · Research Notes (IO-01) · Watchlist Status (WO-01) · Portfolio References (PO-01) · Recent Events · Outstanding Questions · Confidence Summary · Evidence References

Every section is assembled from existing modules with provenance preserved.

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `python -m company_workspace --company TCS` | `GET /v1/company-workspace/{ticker}` |
| `--timeline TCS` | `GET /v1/company-workspace/{ticker}/timeline` |
| `--research TCS` | `GET /v1/company-workspace/{ticker}/research` |
| `--evidence TCS` | `GET /v1/company-workspace/{ticker}/evidence` |

Contracts: shared Office SDK `office_response` only — no custom response models.

---

# 4. Events (PEB-01)

Subscribes (refresh views only — no analysis):

- `company.research.completed`
- `business_quality.updated`
- `management_execution.updated`
- `watchlist.*`
- `portfolio.*`

---

# 5. Mission Control panels

Companies viewed · Workspace refreshes · Coverage · Evidence completeness

---

# 6. Guardrails

Never: run FIRE · modify evidence · modify scores · BUY/SELL · forecast · value companies.
