# FIRE-06 — Business Quality Engine (BQE)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — deterministic synthesis |
| **Workstream** | FIRE-06 |
| **Package** | `intelligence-engine/business_quality/` |
| **Consumes** | Warehouse · DME · FIRE-01…05 · FKB (pillar weights) |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB core · FIRE-01…05 |

> FIRE-06 answers: *Based on all available evidence, how has the underlying quality of the business evolved?*

---

# 1. Mission

Synthesis module. Combines existing FIRE outputs into structured **pillar scores**. Does not invent evidence. No LLM · No BUY/SELL · No valuation.

**Architectural constraint:** pillar scores are primary; overall score is derived from them (never the reverse).

---

# 2. Pillars

1. Growth Quality  
2. Profitability Quality  
3. Cash Flow Quality  
4. Balance Sheet Quality  
5. Capital Allocation Quality  
6. Management Execution *(reuses FIRE-05 — no duplicated logic)*  
7. Business Model Stability  

Weights loaded from FKB (`knowledge.quality_weight` / `list_quality_weights`). Missing pillars are renormalized out of the overall score.

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--company TCS` | `GET /v1/business-quality/company/{ticker}` |
| `--quality TCS` | `GET /v1/business-quality/company/{ticker}/quality` |
| `--pillars TCS` | `GET /v1/business-quality/company/{ticker}/pillars` |

---

# 4. Business Quality Report (BQR)

1. Executive Summary · 2 Overall Quality · 3 Growth · 4 Profitability · 5 Cash · 6 Balance Sheet · 7 Capital Allocation · 8 Management Execution · 9 Business Model · 10 Strengths · 11 Weaknesses · 12 Confidence · 13 Evidence References

---

# 5. Language guardrails

Never: “excellent company”, “poor company”, “great investment”, “bad investment”.  
Only: Business Quality Score · Evidence · Confidence · Pillar assessments.
