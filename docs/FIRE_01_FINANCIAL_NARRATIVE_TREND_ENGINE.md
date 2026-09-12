# FIRE-01 — Financial Narrative & Trend Engine

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — evidence-backed intelligence (consumer) |
| **Workstream** | FIRE-01 |
| **Package** | `intelligence-engine/financial_intelligence/` |
| **Consumes** | Financial Warehouse · Derived Metrics · Validation · Coverage |
| **Frozen** | FSE collectors · Orchestrator · Parser · VFQE · Warehouse · DME · FDO |

> **Intent:** Answer *What happened financially?* before *What should an investor do?*  
> FIRE never invents facts, never mutates warehouse data, never issues BUY/SELL.

---

# 1. Mission

Transform validated financial facts into evidence-backed financial intelligence.

Every statement references warehouse evidence (metric · period · warehouse version · values).

---

# 2. Inputs (read-only)

| Source | Role |
| --- | --- |
| Financial Warehouse contracts / metric history | Validated facts |
| Derived Metrics contracts | Margins, ROE/ROCE, leverage, FCF |
| Validation metadata | Approval / quality |
| Coverage metadata (ECD / FDO) | History depth / completeness |

Never read collectors or raw evidence directly.

---

# 3. Engines (deterministic)

| Engine | Role |
| --- | --- |
| Trend Engine | QoQ · YoY · 3y · 5y direction for core metrics |
| Narrative Engine | Template explanations (no LLM opinions) |
| Quality Engine | Cash conversion, leverage, earnings quality signals |
| Confidence | High / Medium / Low from coverage + validation + history |

---

# 4. Output

Structured `Financial Intelligence Report` (JSON) with sections 1–13 and findings:

`Finding · Category · Severity · Evidence · Confidence · Narrative`

---

# 5. Surfaces

| CLI | REST |
| --- | --- |
| `python -m financial_intelligence --financial-intelligence TCS` | `GET /v1/financial-intelligence/company/{ticker}` |
| `python -m financial_intelligence --financial-findings TCS` | `GET /v1/financial-intelligence/findings/{ticker}` |
| `python -m financial_intelligence --health` | `GET /v1/financial-intelligence/health` |
| | `GET /v1/financial-intelligence/dashboard` |

---

# 6. Non-goals

No BUY · No SELL · No Target Price · No Forecast · No DCF · No Recommendations · No LLM-generated opinions.
