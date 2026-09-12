# Phase 12 — Sprint 12.5: Market Forecast Intelligence (MKFI)

**Status:** Implemented in `intelligence-engine/market_forecast_intelligence/`  
**Version:** 0.1.0  
**Depends on:** CMKTP (12.1), HMKIP (12.2), MKRI (12.3), HMKAI (12.4); inherits Macro MFI (10.5) and SFI (11.5)  
**Pattern:** Market twin of Macro MFI / Sector SFI  
**Note:** Programme short is **MKFI** to avoid collision with Macroeconomic Forecast Intelligence (**MFI**).

---

## Objective

Generate evidence-based **Bull / Base / Bear** market pathways with probabilities, confidence scores and supporting evidence — never a single predicted outcome.

MKFI is AGI's institutional market strategist. It answers outlook, sustainability, correction probability, sector leadership, policy transmission and thesis invalidation questions using AGI-owned knowledge only.

---

## Architecture

```text
Continuous Market Knowledge (CMKTP)
        │
Historical Market Intelligence (HMKIP)
        │
Market Relationship Intelligence (MKRI)
        │
Historical Market Analogues (HMKAI)
        │
Macro Forecast Intelligence (MFI inheritance)
        │
Sector Forecast Intelligence (SFI inheritance)
        │
        ▼
Market Forecast Bundle
        │
Scenario Engine → Bull / Base / Bear
        │
Probability Engine · Confidence Engine
        │
Risk & Catalyst Engine · Market Impact Engine
        │
Forecast Publication → Investment Office
```

---

## Guardrails

* AGI-owned knowledge only — `providers_queried` always `[]`
* Ask never collects or rebuilds
* No BUY/SELL, no target prices, no single-path certainty
* Macro assumptions inherited from MFI — MKFI does not create an independent macro view
* Sector leadership tips inherited from SFI
* Every scenario is evidence-linked (analogues, relationships, research, CMKTP/HMKIP tips)

---

## Forecast horizons

Independent forecasts for:

* 1 Month
* 3 Months
* 6 Months
* 12 Months

---

## Forecast dimensions

Market direction · Breadth · Liquidity · Volatility · Institutional flows · Leadership · Cross-asset behaviour

---

## Supported markets

India · Global

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/mkfi/health` | Programme health |
| GET | `/v1/market/forecast` | All-market / all-horizon summary |
| GET | `/v1/market/forecast/india` | India forecast |
| GET | `/v1/market/forecast/{market}` | Per-market forecast |
| GET | `/v1/market/scenarios` | BBB scenarios |
| GET | `/v1/market/probability` | Distribution + confidence |
| GET | `/v1/market/catalysts` | Key catalysts |
| GET | `/v1/market/risks` | Risks + invalidation alerts |
| GET | `/v1/market/forecast/report` | Full report |
| GET | `/v1/market/forecast/history` | Version history |
| GET | `/v1/market/forecast/dashboard` | Mission Control JSON |
| POST | `/v1/market/forecast/run` | Ops publish only |
| GET | `/v1/admin/market-forecast` | HTML ops board |

---

## LangSmith traces

```text
market_forecast_bundle
market_scenario_generation
market_probability
market_confidence
market_risk_engine
market_catalyst_engine
market_forecast_validation
market_forecast_publication
```

---

## Mission Control

**Market Forecast Intelligence** board (`phase: 12.5`):

* Current market outlook
* Bull/Base/Bear scenarios
* Scenario probabilities / confidence trends
* Forecast horizons
* Key catalysts / risks / invalidation alerts
* Sector leadership forecast
* Forecast revisions / accuracy tracking
* Macro and sector inheritance

---

## Soft consumers

* **IFI** soft-reads MKFI for market `forecast_intelligence` via `MKFI_KRIG` (store-only).
* MKFI soft-consumes CMKTP, HMKIP, MKRI, HMKAI and inherits MFI / SFI tips.
* Downstream cascade: Sector Forecast · Company Forecast · Portfolio Intelligence · Investment Office.

---

## Success criteria

* Evidence-based Bull/Base/Bear scenarios for multiple horizons.
* Forecasts derived from AGI Market / Macro / Sector / Company intelligence — not live feeds.
* Every forecast includes probabilities, confidence, supporting relationships, historical analogues, catalysts, risks and invalidation conditions.
* Forecast quality, revisions and accuracy are observable via Mission Control and LangSmith.

---

## Phase 12 complete

```text
12.1 Continuous Market Knowledge (CMKTP)
          │
          ▼
12.2 Historical Market Intelligence (HMKIP)
          │
          ▼
12.3 Market Relationship Intelligence (MKRI)
          │
          ▼
12.4 Historical Market Analogue Intelligence (HMKAI)
          │
          ▼
12.5 Market Forecast Intelligence (MKFI)
```

| Sprint | Module | Status |
|---|---|---|
| ✅ 12.1 | CMKTP — Continuous Market Knowledge | Complete |
| ✅ 12.2 | HMKIP — Historical Market Intelligence | Complete |
| ✅ 12.3 | MKRI — Market Relationship Intelligence | Complete |
| ✅ 12.4 | HMKAI — Historical Market Analogue Intelligence | Complete |
| ✅ 12.5 | MKFI — Market Forecast Intelligence | Complete |

---

## What comes next: Phase 13

With Company, Macro, Sector and Market Intelligence complete, the next major institutional capability is a **Portfolio Intelligence Platform** — synthesising prior layers for allocation, sizing, risk decomposition, scenario stress, factor exposures, attribution, monitoring and constraint-aware optimisation.
