# FSE-ECD — Evidence Coverage Dashboard

## Measurement Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production measurement surface |
| **Workstream** | FSE-ECD |
| **Package** | `intelligence-engine/financial_statements_engine/evidence_coverage/` |
| **Question** | How many companies do we have — at each stage of the financial statements pipeline? |
| **Depends on** | FSE-01…FSE-07 stores (collection · parse · validate · warehouse · DME) + HD financial series |

> **Intent:** One funnel dashboard that answers institutional coverage — not per-document extraction audit (that remains FSE-04.2). Target for every stage is **100%** of the selected universe.

---

## Funnel metrics (all target 100%)

| Metric | Meaning |
| --- | --- |
| Companies discovered | In-universe companies known to the system (listed / discovered / present in any evidence store) |
| Companies with latest annual filing | Annual filing present for the latest expected fiscal year window |
| Companies with latest quarterly filing | Quarterly filing present for the latest expected quarter window |
| Companies parsed | Canonical draft / coverage matrix exists |
| Companies validated | VFQE approval publishable (`APPROVED` / `APPROVED_WITH_WARNINGS`) |
| Companies published | Validated facts in Financial Warehouse (or legacy published pack) |
| Companies with derived metrics | At least one DME metric version stored |

---

## Universes

`gold` · `nifty50` · `nifty100` · `nifty500` · `hd` (tickers present on Historical Depth disk)

Default operational universe: **nifty500** (coverage-before-depth).

---

## Surfaces

| Surface | Path / flag |
| --- | --- |
| Health | `GET /financial-statements/evidence-coverage/health` · `--ecd-health` |
| Dashboard | `…/dashboard?universe=nifty500` · `--ecd-dashboard [universe]` |
| Company row | `…/company/{ticker}` · `--ecd-company TICKER` |

---

## Success criteria

* Single answer to “how many companies do we have?” per stage
* Deterministic stage detection from existing stores (no new collectors)
* Gaps listed explicitly (missing annual / quarterly / parse / validate / publish / DME)
* Mission Control can render the funnel without reading internal tables
