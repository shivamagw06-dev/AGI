# Phase 11 — Sprint 11.5: Sector Forecast Intelligence (SFI)

**Status:** Implemented in `intelligence-engine/sector_forecast_intelligence/`  
**Version:** 0.1.0  
**Depends on:** CSKP (11.1), HSIP (11.2), SRI (11.3), HSAI (11.4); inherits macro from MFI (10.5)  
**Pattern:** Sector twin of MFI (Sprint 10.5)

---

## Objective

Generate evidence-based **Bull / Base / Bear** sector pathways with probabilities, confidence scores and supporting evidence — never a single predicted outcome.

---

## Architecture

```text
Continuous Sector Knowledge
        │
Historical Sector Intelligence
        │
Sector Relationship Intelligence
        │
Historical Sector Analogues
        │
Macro Forecast Intelligence (inherited)
        │
        ▼
Sector Forecast Bundle
        │
Scenario Intelligence → Bull / Base / Bear
        │
Probability Engine · Confidence Engine
        │
Sector → Company Impact Engine
        │
Forecast Publication → Investment Office
```

---

## Guardrails

* AGI-owned knowledge only — `providers_queried` always `[]`
* Ask never collects or rebuilds
* No BUY/SELL, no target prices, no single-path certainty
* Macro assumptions inherited from MFI — SFI does not create an independent macro view
* Every scenario is evidence-linked (analogues, relationships, research, CSKP/HSIP tips)

---

## Supported sectors

Banking · IT Services · FMCG · Auto · Capital Goods · Pharma

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/sfi/health` | Programme health |
| GET | `/v1/sector/forecast` | All-sector summary |
| GET | `/v1/sector/forecast/{sector}` | Sector forecast |
| GET | `/v1/sector/scenarios` | BBB scenarios |
| GET | `/v1/sector/probability` | Distribution + confidence |
| GET | `/v1/sector/forecast/report` | Full report |
| GET | `/v1/sector/forecast/history` | Version history |
| POST | `/v1/sector/forecast/run` | Ops publish only |
| GET | `/v1/admin/sector-forecast` | HTML ops board |

---

## LangSmith traces

```text
sector_forecast_bundle
sector_scenario_generation
sector_probability
sector_confidence
sector_company_impact
sector_forecast_validation
sector_forecast_publication
```

---

## Mission Control

**Sector Forecast Intelligence** board (`phase: 11.5`):

* Current sector outlook
* Bull/Base/Bear scenarios
* Probability / confidence
* Catalysts / risks
* Company impact summaries
* Macro inheritance
* Forecast revisions

---

## Soft consumers

* **IFI** soft-reads SFI for sector `forecast_intelligence` (store-only).
* SFI soft-consumes CSKP, HSIP, SRI, HSAI and inherits MFI probability/scenario tips.

---

## Success criteria

* Every supported sector has evidence-based Bull/Base/Bear scenarios.
* Forecasts inherit macro assumptions from MFI and cascade to companies.
* Each forecast is backed by analogues, relationships, research and confidence scoring.
* Forecasts are versioned, explainable and observable via Mission Control + LangSmith.
* Investment Office / IFI consume SFI without external providers.

---

## Phase 11 complete

| Sprint | Module | Status |
|---|---|---|
| ✅ 11.1 | CSKP | Continuous sector knowledge |
| ✅ 11.2 | HSIP | Historical sector memory |
| ✅ 11.3 | SRI | Sector relationship intelligence |
| ✅ 11.4 | HSAI | Historical sector analogue intelligence |
| ✅ 11.5 | SFI | Sector forecast intelligence |

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

Company, Macro and Sector domains now share the same lifecycle.

### After Phase 11

**Phase 12: Market Intelligence Platform** — market regimes, breadth, liquidity, volatility, leadership/rotation, cross-asset relationships and institutional positioning. Sprint **12.1 CMKTP** is documented in `docs/PHASE12_SPRINT_12_1_CMKTP.md`.
