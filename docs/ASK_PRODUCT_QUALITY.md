# Ask Product Quality & Institutional Answer Excellence (AQE) v1.0

**Phase 9.2** — product quality over the existing intelligence stack.

## Vision

Phase 9.1 (IFAC) completed institutional composition. Phase 9.2 raises production
regression scores by improving routing, entity/metadata resolution, evidence
ranking, BI pedagogy, and answer quality — **without adding new intelligence engines**.

Path remains:

```
Warehouse → UVE → HVIE → VPAE → VARIE → RIE → FIE → MIE → Market Intelligence → IFAC
```

## What changed

### 1. KUL routing
- Macro-finance definitions (`equity risk premium`, `inflation`, …) route to
  `financial_concepts` / academy, not live MIE.
- Comparison menus put **BI + CapIQ/memory/KF early** so evidence fusion survives
  provider budgets.
- Default `plan_and_gather` budget raised to 12 providers.

### 2. Entity resolution / unsupported globals
- Business pedagogy questions about Costco / Visa / Mastercard / Ferrari / Toyota
  allow the planner with **no CapIQ ticker bind** (`pedagogy_only`).
- Bare unsupported names still refuse (no hallucination).
- `should_short_circuit` respects `allow_planner=True`.

### 3. Metadata routing
- Market cap / enterprise value / ISIN fields recognized when present on identity.
- Empty market-data fields fall through to KUL instead of empty short-circuits.

### 4. IFAC / fusion quality
- Generic template leads (`For unknown…`, `Business type: unknown`, stock-market Q&A
  dumps) are rejected as headlines.
- Missing intelligence uses institutional explanations (HVIE / FIE / MIE / BI).

### 5. BI integration
- Named pedagogy for Mastercard; richer Visa / Ferrari contrast keys.
- Unsupported-global pedagogy reaches BI via KUL/UKO.

### 6. AQE module
Package: `intelligence-engine/ask_product_quality/`

| Surface | Purpose |
|---------|---------|
| `routing.inspect_routing` | Intent → entity → domain → providers |
| `evidence_rank.rank_evidence` | Confidence / freshness / warehouse / relevance |
| `confidence.calibrate` | Never invent arbitrary defaults |
| `production.quality_gate` | DQIV-style product checks |
| `production.dashboard` | Regression quality probes |

## APIs (non-breaking)

| Method | Path |
|--------|------|
| GET | `/v1/aqe/health` |
| GET | `/v1/aqe/dashboard` |
| POST | `/v1/aqe/inspect` |
| POST | `/v1/aqe/quality-gate` |

BFF mirrors under `/api/intelligence/aqe/*`.

Existing `/api/ui/search`, `/v1/ask`, `/v1/kul`, `/v1/ifac` unchanged in contract.

## Admin

| Route | Page |
|-------|------|
| `/admin/aqe` | Ask Product Quality dashboard |
| `/admin/kul` | KUL routing inspector |
| `/admin/ifac` | IFAC composer (+ product-quality links) |

## Success criteria (targets)

| Metric | Target |
|--------|--------|
| KUL Acceptance | ≥95% |
| Answer Quality | ≥95% |
| Company Metadata Routing | ≥99% |
| BI Integration | ≥95% |
| Founder Evaluation | ≥95% |
| Golden Business | ≥95% |
| Core Platform | ≥95% |
| Exit failures | 0 |
| Hallucination rate | 0% |

## Constraints

- Do **not** add new intelligence engines
- Do **not** call live vendors during Ask
- Do **not** bypass IFAC
- Do **not** invent CapIQ binds for unsupported globals

## Tests

```bash
cd intelligence-engine
python3 -m pytest ask_product_quality/tests/test_aqe_core.py -q
```
