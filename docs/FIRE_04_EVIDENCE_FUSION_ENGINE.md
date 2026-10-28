# FIRE-04 — Evidence Fusion Engine (EFE)

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — deterministic cross-evidence fusion |
| **Workstream** | FIRE-04 |
| **Package** | `intelligence-engine/evidence_fusion/` |
| **Consumes** | Warehouse · DME · FIRE-01 · FIRE-02 · FIRE-03 · FKB |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE-01 · FIRE-02 · FIRE-03 · Mission Control architecture |

> FIRE-04 answers: *Does all available evidence agree?*  
> It determines whether quantitative and qualitative evidence tell a consistent story.

---

# 1. Mission

Cross-evidence reasoning layer. Compare management / business statements (FIRE-03) with financial trends (FIRE-01), relationships (FIRE-02), and warehouse metrics.

No LLM · No BUY/SELL · No forecasts · No valuation · Never mutates data · Never reads collectors.

---

# 2. Fusion outcomes

| Result | Meaning |
| --- | --- |
| **Supported** | Financial evidence aligns with the statement |
| **Partially Supported** | Mixed signals across metrics / sources |
| **Not Supported** | Financial evidence conflicts with the statement |
| **Insufficient Evidence** | Topic discussed, but no measurable financial evidence yet |

Never infer intent. Never judge management honesty.

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--company TCS` | `GET /v1/evidence-fusion/company/{ticker}` |
| `--supported TCS` | `GET /v1/evidence-fusion/company/{ticker}/supported` |
| `--conflicts TCS` | `GET /v1/evidence-fusion/company/{ticker}/conflicts` |
| `--alignment TCS` | `GET /v1/evidence-fusion/company/{ticker}/alignment` |

---

# 4. Evidence Fusion Report (EFR)

1. Executive Summary  
2. Supported Statements  
3. Partially Supported Statements  
4. Unsupported Statements  
5. Insufficient Evidence  
6. Financial Consistency  
7. Capital Allocation Consistency  
8. Risk Consistency  
9. Guidance Consistency  
10. Overall Evidence Alignment  

---

# 5. Non-goals

No recommendations · No valuation · No forecasts · No target prices · No sentiment · No macro · No analyst opinions · No hallucinated conclusions.
