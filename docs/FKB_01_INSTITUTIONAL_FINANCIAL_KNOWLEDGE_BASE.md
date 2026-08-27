# FKB-01 — Institutional Financial Knowledge Base

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — canonical knowledge (read-only) |
| **Workstream** | FKB-01 |
| **Package** | `intelligence-engine/financial_knowledge/` |
| **Consumers** | FIRE-01 · FIRE-02 · future FIRE · validation · explainability |
| **Frozen** | FSE · FDO · FIRE analysis logic · Warehouse |

> **FSE** stores facts. **FIRE** analyses facts. **FKB** defines what financial concepts mean.

---

# 1. Mission

Single source of truth for financial concepts, relationships, thresholds, and institutional interpretations.

Nothing inside FKB performs analysis.

---

# 2. Surfaces

| CLI | REST |
| --- | --- |
| `--metric ROCE` | `GET /v1/knowledge/metrics` |
| `--ratio OperatingMargin` | `GET /v1/knowledge/ratios` |
| `--relationship PAT_OCF` | `GET /v1/knowledge/relationships` |
| `--glossary OperatingLeverage` | `GET /v1/knowledge/glossary` |
| `--threshold InterestCoverage` | `GET /v1/knowledge/thresholds` |
| `--health` / `--dashboard` | `GET /v1/knowledge/health` · `/dashboard` |

Registry: `knowledge.metric("Revenue")`, `knowledge.ratio("ROCE")`, …

---

# 3. Non-goals

No BUY/SELL · No forecasts · No valuation · No parsing · No financial calculations · No warehouse changes · No FIRE redesign.
