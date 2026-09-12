# Phase 11 — Sprint 11.4: Historical Sector Analogue Intelligence (HSAI)

**Status:** Implemented in `intelligence-engine/historical_sector_analogue_intelligence/`  
**Version:** 0.1.0  
**Depends on:** CSKP (11.1), HSIP (11.2), SRI (11.3); soft HMIP tips for macro overlays  
**Pattern:** Sector twin of HMAI (Sprint 10.4)  
**Enables:** SFI (11.5) sector forecast scenarios

---

## Objective

Identify and rank historical sector environments most similar to the current sector state using multi-dimensional, deterministic similarity analysis.

Core question: *Have we seen this sector environment before?*

---

## Architecture

```text
Current Sector Knowledge (CSKP)
        │
Historical Sector Intelligence (HSIP)
        │
Sector Relationship Intelligence (SRI)
        │
Historical Macro tips (HMIP)
        │
        ▼
Sector Analogue Engine
        │
Similarity Engine
        │
Ranking Engine
        │
Historical Sector Analogues
        │
Knowledge Retrieval Gateway
        │
Sector Forecast Intelligence (11.5)
```

---

## Similarity dimensions

| Dimension | Weight | Primary tip |
|---|---|---|
| Revenue Growth | 0.12 | HSIP / catalog |
| Earnings Growth | 0.10 | HSIP / catalog |
| Margin Profile | 0.10 | HSIP / catalog |
| ROE | 0.10 | HSIP / catalog |
| Valuation | 0.12 | PE tip |
| Relative Performance | 0.08 | vs NIFTY |
| Interest-Rate Environment | 0.10 | HMIP Repo |
| Inflation Environment | 0.08 | HMIP CPI |
| Currency Environment | 0.06 | HMIP USDINR |
| Policy Environment | 0.08 | policy support index |
| Industry Structure | 0.06 | concentration / util index |

Scoring: `weighted_relative_distance` — deterministic and reproducible. Weights sum to 1.0.

---

## Supported sectors

Banking · IT Services · FMCG · Auto · Capital Goods · Pharma

Each carries historical regimes (2008, 2013, 2017, 2020, 2022, 2025) plus a current 2026 tip vector and historical outcome bundles.

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/hsai/health` | Programme health |
| GET | `/v1/sector/analogues` | Ranked analogues |
| GET | `/v1/sector/analogues/{sector}` | Sector surface |
| GET | `/v1/sector/analogues/search` | NL / period filters |
| GET | `/v1/sector/regime/current` | Current regime vector |
| GET | `/v1/sector/regime/history` | Historical regimes |
| GET | `/v1/sector/analogues/dashboard` | Mission Control payload |
| POST | `/v1/sector/analogues/run` | Ops rebuild only |
| GET | `/v1/admin/sector-analogues` | HTML ops board |

Read APIs never rebuild catalogues. `providers_queried` is always `[]`.

---

## LangSmith traces

```text
sector_analogue_search
sector_similarity_scoring
sector_analogue_ranking
sector_analogue_retrieval
sector_analogue_refresh
```

---

## Mission Control

**Historical Sector Analogue** board (`phase: 11.4`):

* Current sector regime
* Top analogue matches
* Similarity / confidence distributions
* Coverage by sector
* Historical completeness
* Analogue freshness

---

## Soft consumers

* **IFI** soft-reads HSAI `forecast_tip` for sector `historical_analogues` (store-only).
* HSAI soft-confirms via CSKP current tips, HSIP timelines, SRI relationships, HMIP macro overlays.

---

## Success criteria

* Supported sectors retrieve comparable historical environments.
* Analogues ranked via deterministic multi-dimension scoring.
* Each analogue includes supporting relationships, research and historical outcome bundles.
* Forecast path can consume analogue bundles without external providers.
* Quality / coverage / freshness observable via Mission Control and LangSmith.

---

## Phase 11 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 11.1 | CSKP | Continuous sector knowledge |
| ✅ 11.2 | HSIP | Historical sector memory |
| ✅ 11.3 | SRI | Sector relationship intelligence |
| ✅ 11.4 | HSAI | Historical sector analogue intelligence |
| ✅ 11.5 | SFI | Sector forecast intelligence |

### Architectural symmetry

```text
Continuous Knowledge
        │
        ▼
Historical Knowledge
        │
        ▼
Relationship Intelligence
        │
        ▼
Historical Analogue Intelligence
        │
        ▼
Forecast Intelligence
```
