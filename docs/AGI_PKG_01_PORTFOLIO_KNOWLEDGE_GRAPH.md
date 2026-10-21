# PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph

**Mission:** Move from single-company intelligence to **portfolio intelligence** — the first brick of the Phase 4 Investment Office.

```text
Portfolio
↓
Companies
↓
Relationships
↓
Portfolio Graph
```

Instead of Axis → Decision alone, AGI now holds:

```text
Portfolio → Axis → Kotak → HDFC → ICICI
```

No Gemini. No GPT. No portfolio optimisation. No rebalancing engine (Sprint 4.4).

## Naming note

| Layer | Package | Workstream |
| --- | --- | --- |
| Holdings **state** (immutable snapshots) | `portfolio_office` | historical PO-01 |
| Portfolio **knowledge graph** (this sprint) | `institutional_portfolio` | **PKG-01** (Phase 4.1 / PO-01 programme) |

API path `/v1/portfolio-graph/*` avoids collisions with `/v1/portfolio-office/*` and `/v1/portfolio/*`.

## InstitutionalPortfolio

```python
InstitutionalPortfolio(
    holdings=[],
    allocations=[],
    exposures=[],
    risks=[],
    decisions=[],
)
```

First-class object for the Investment Office — composed from holdings + company decisions + company graphs.

## Package

`intelligence-engine/institutional_portfolio/`

| Module | Role |
| --- | --- |
| `portfolio_graph.py` | Build Portfolio → Company → Sector/Decision/Correlation graph |
| `portfolio_entities.py` | Entities, relationships, `InstitutionalPortfolio` |
| `allocation.py` | Weight bands / roles (no optimisation) |
| `exposures.py` | Sector, country, industry, recommendation mix |
| `correlations.py` | Deterministic structural correlation proxies |
| `concentration.py` | HHI, top weights, concentration risks |
| `diagnostics.py` | Quality gates |
| `production.py` | Health, build/get, Mission Control soft slice |

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_portfolio
PYTHONPATH=. python3 -m institutional_portfolio --portfolio-id agi-core-equity --json
```

API:

- `GET /v1/portfolio-graph/health`
- `GET /v1/portfolio-graph/{portfolio_id}`
- `GET /v1/portfolio-graph/{portfolio_id}/portfolio`
- `POST /v1/portfolio-graph`

BFF: `/api/intelligence/portfolio-graph/*`

## UI

`/agi/portfolio` → **Portfolio Knowledge Graph** panel (entities, holdings→decisions, sector exposure, concentration risks).

Mission Control → Portfolio Knowledge Graph soft board.

## Out of scope (later Phase 4 sprints)

CIO portfolio decisions · portfolio risk engine · allocation sizing · portfolio scenarios · portfolio observations · committee · CIO workspace
