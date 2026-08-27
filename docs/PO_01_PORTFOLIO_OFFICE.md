# PO-01 — Portfolio Office

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — Portfolio Domain (canonical state) |
| **Workstream** | PO-01 |
| **Package** | `intelligence-engine/portfolio_office/` |
| **Consumes** | Office SDK · FIRE-05 · FIRE-06 · holdings · company master · market reference |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE · Office SDK · IO-01 · CIO-01 |

> Portfolio Office answers: *What does this portfolio currently look like, based on validated holdings and existing intelligence?*

---

# 1. Mission

Canonical portfolio state layer.

- Never optimises or rebalances  
- Never recommends BUY / SELL  
- Never recalculates FIRE-05 / FIRE-06  
- Snapshots are **immutable** point-in-time records  

---

# 2. Model

`Portfolio` · `Holding` · `CashPosition` · `PortfolioSnapshot` · `PortfolioMetadata`

---

# 3. Surfaces

| CLI | REST |
| --- | --- |
| `--portfolio Core` | `GET /v1/portfolio-office/{id}` |
| `--summary Core` | `GET .../holdings` · `/exposures` · `/quality` · `/concentration` |
| `--snapshot Core` | `POST /v1/portfolio-office` · `POST .../snapshot` |

> Path prefix `/v1/portfolio-office/*` is intentional: `/v1/portfolio/*` is already used by Institutional Portfolio Office (ideas OS). PO-01 stays additive.

Office SDK: `office_id=po-01`
