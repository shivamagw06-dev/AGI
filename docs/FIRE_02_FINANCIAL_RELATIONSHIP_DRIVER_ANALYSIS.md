# FIRE-02 — Financial Relationship & Driver Analysis

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — deterministic relationship analysis |
| **Workstream** | FIRE-02 |
| **Package** | `intelligence-engine/financial_intelligence/drivers/` |
| **Depends on** | FIRE-01 inventory/confidence · Financial Warehouse · DME |
| **Frozen** | FSE · FDO · FIRE-01 report shape · Mission Control architecture |

> FIRE-01 answers *What changed?*  
> FIRE-02 answers *Which financial relationships explain those changes?*

---

# 1. Mission

Deterministic cross-statement relationship analysis over validated warehouse facts.

No LLM · No forecasts · No recommendations · Never mutates data.

---

# 2. Driver categories

Revenue · Margin · Cash Flow · Working Capital · Balance Sheet · Capital Allocation · Returns

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--financial-drivers TCS` | `GET /v1/financial-intelligence/company/{ticker}/drivers` |
| `--financial-relationships TCS` | `GET /v1/financial-intelligence/company/{ticker}/relationships` |

---

# 4. Non-goals

No BUY/SELL · No valuation · No DCF · No forecasting · No macro/news interpretation.
