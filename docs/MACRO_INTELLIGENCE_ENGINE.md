# Macro Intelligence Engine (MIE) — Phase 9.0

**Status:** Implemented  
**Package:** `intelligence-engine/macro_intelligence_engine/`  
**Canonical API prefix:** `/v1/mie/*`  
**Admin:** `/admin/macro-runtime`  
**Valuation Terminal:** Macro tab

> Legacy sprint surfaces remain under `/v1/macro/*` (CMKP, HMIP, MRI, HMAI, MFI).  
> Phase 9.0 institutional MIE uses `/v1/mie/*` to avoid collision.

## Vision

MIE answers: **What is happening in the macro environment, why does it matter, and how should that influence sector, industry, and company research?**

It is **not** a GDP prediction engine and never emits BUY/SELL.

## Architecture

```
External Data (RBI • MOSPI • FRED • …)  →  Macro Warehouse / CMKP collectors
                                              │
                                              ▼
                                   Macro Intelligence Engine
                                              │
                    ┌───────────────┬─────────┼──────────┐
                    ▼               ▼         ▼          ▼
            Market Intelligence   RIE       FIE    Portfolio Office
```

One-way flow. Compose time never calls vendors. MIE consumes warehouse + CMKP/HMIP/MRI/HMAI/MFI.

## Design principles

| Must | Must not |
|---|---|
| Warehouse-first | Call vendors at compose/Ask time |
| Explain every conclusion | Predict GDP as a point estimate |
| Expose confidence | Generate BUY/SELL |
| Version / append history | Opaque AI-only reasoning |
| Probabilities sum to 100% | UI recalculation of macro state |

## Modules

Executive · Dashboard · Regime · Cycle · Economy · Inflation · Rates · Liquidity · Currency · Commodities · Bonds · Fiscal · External · Sector Impact · Industry Impact · Company Exposure · Attribution · Forecast (directional) · Scenarios · Risks · Relationships · Confidence

## Warehouse tabs

`macro_series` · `macro_latest` · `macro_events` · `macro_regimes` · `macro_history` · `macro_forecasts` · `macro_relationships` · `macro_alerts` · `macro_calendar` · `macro_runtime`

## APIs

```bash
GET  /v1/mie/health
GET  /v1/mie/dashboard
GET  /v1/mie/pack
GET  /v1/mie/regime
GET  /v1/mie/economy
GET  /v1/mie/inflation
GET  /v1/mie/rates
GET  /v1/mie/liquidity
GET  /v1/mie/currency
GET  /v1/mie/commodities
GET  /v1/mie/bonds
GET  /v1/mie/fiscal
GET  /v1/mie/external
GET  /v1/mie/sector-impact
GET  /v1/mie/industry-impact
GET  /v1/mie/company-impact/{symbol}
GET  /v1/mie/forecast
GET  /v1/mie/scenarios
GET  /v1/mie/relationships
GET  /v1/mie/risks

GET  /v1/mie/runtime/status
GET  /v1/mie/runtime/board
POST /v1/mie/runtime/start|stop|resume|run
```

BFF: `/api/intelligence/mie/*`  
Client: `getMie*` / `postMieRuntime*` in `src/lib/intelligenceApi.js`

## Runtime cadence

| Trigger | Action |
|---|---|
| Daily | FX, commodities, yields, liquidity |
| Weekly | Slower indicators + relationships |
| Monthly | CPI, IIP, PMI, credit, fiscal |
| Quarterly | GDP context, sector impact, forecasts |
| Event | RBI / Budget / major CB / geopolitics |

## Downstream consumers

- **Market Intelligence** — regime, sector impact, liquidity, inflation, rates  
- **RIE** — macro risks / catalysts / industry outlook  
- **FIE** — soft-consumes MIE regime + scenarios in evidence bundle  
- **Portfolio Office** — sector tilts, FX/duration/commodity/liquidity exposures  
- **Ask / KUL** — provider `macro_intelligence_engine`

## Success criteria

| Metric | Target |
|---|---|
| Sector impact coverage | 100% (11 sectors) |
| Explainability | 100% |
| Probability validation | 100% |
| BUY/SELL recommendations | 0 |
| GDP point predictions | 0 |

## Tests

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest macro_intelligence_engine/tests/test_mie.py -q
```
