# Forecast Intelligence Engine (FIE) — Phase 8.5

**Status:** Implemented  
**Package:** `intelligence-engine/forecast_intelligence_engine/`  
**Canonical API prefix:** `/v1/fie/*`  
**Admin:** `/admin/forecast-runtime`  
**Valuation Terminal:** Forecast tab

> Legacy scenario layer remains at `/v1/forecast/*` (`forecast_intelligence`).  
> Phase 8.5 institutional FIE uses `/v1/fie/*` to avoid collision.

## Vision

FIE answers: **What is the most probable future path of this business, its valuation, and its risks?**

It is **not** a stock-price prediction engine. It never emits BUY/SELL, never invents unsupported assumptions, and never emits target prices.

## Architecture

```
Warehouse → UVE → HVIE → VPAE → VARIE → RIE → FIE
                                              ├→ Valuation Terminal
                                              ├→ Ask AI (KUL provider)
                                              └→ Portfolio Office
```

One-way flow. FIE never recalculates upstream intelligence and never calls vendors (Upstox, Yahoo, etc.).

## Design principles

| Must | Must not |
|---|---|
| Explain every forecast | Call Upstox / Yahoo |
| Expose confidence + assumptions | Download analyst reports |
| Version + append-only history | Perform UI calculations |
| Remain deterministic | Generate BUY/SELL |
| Probabilities sum to 100% | Emit target prices |
| DQIV reject unsupported packs | Invent hidden assumptions |

## Modules

1. Executive Forecast  
2. Business Forecast (Revenue, EBITDA, EBIT, PAT, EPS, BV, OCF, FCF · NQ / FY+1…FY+5)  
3. Growth Engine  
4. Profitability Engine  
5. Balance Sheet Engine  
6. Valuation Outlook (ranges only — never target price)  
7. Scenario Engine (Bull / Base / Bear)  
8. Probability Engine (must total 100%)  
9. Assumption Engine  
10. Sensitivity Engine  
11. Risk Engine  
12. Catalyst Engine  
13. Confidence Engine  
14. Explainability (Observed / Derived / Assumed)  
15. Forecast Timeline (append-only)  
16. Forecast Accuracy  
17. Forecast Learning (future vintages only; never rewrite history)

## Ensemble models

Historical Trend · Financial Statement · Valuation (HVIE/UVE/VARIE) · Business Quality (RIE) · Market Regime — combined with probability / confidence weighting.

## Warehouse tabs (append-oriented)

| Tab | Mode |
|---|---|
| `forecast_company` | master summary |
| `forecast_history` | append |
| `forecast_scenarios` | append |
| `forecast_assumptions` | append |
| `forecast_confidence` | append |
| `forecast_accuracy` | append |
| `forecast_runtime` | runtime progress |

## APIs

```bash
GET  /v1/fie/health
GET  /v1/fie/dashboard
GET  /v1/fie/coverage
GET  /v1/fie/company/{symbol}
GET  /v1/fie/business/{symbol}
GET  /v1/fie/growth/{symbol}
GET  /v1/fie/profitability/{symbol}
GET  /v1/fie/balance-sheet/{symbol}
GET  /v1/fie/valuation/{symbol}
GET  /v1/fie/scenarios/{symbol}
GET  /v1/fie/sensitivity/{symbol}
GET  /v1/fie/risks/{symbol}
GET  /v1/fie/catalysts/{symbol}
GET  /v1/fie/confidence/{symbol}
GET  /v1/fie/history/{symbol}
GET  /v1/fie/accuracy/{symbol}

GET  /v1/fie/runtime/status
GET  /v1/fie/runtime/board
POST /v1/fie/runtime/start
POST /v1/fie/runtime/stop
POST /v1/fie/runtime/resume
POST /v1/fie/runtime/run
```

BFF: `/api/intelligence/fie/*`  
Client: `getFie*` / `postFieRuntime*` in `src/lib/intelligenceApi.js`

## Runtime

| Trigger | Action |
|---|---|
| Bootstrap | Full forecast → store → version |
| Quarterly results | Forward update (future only) |
| HVIE change | Refresh valuation outlook |
| RIE change | Refresh confidence |
| Market regime change | Refresh scenarios |
| Monthly | Refresh all forecasts |
| Quarterly | Accuracy → learning → next vintage |

Admin board tracks: universe, complete, running, waiting HVIE/RIE/statements, failed, coverage, confidence distribution, accuracy.

## Ask AI / KUL

Provider id: `forecast_intelligence_engine`  
Ask reads FIE via `ask_slice` only — never recalculates.

Example questions: 3-year outlook, bull/bear explanation, confidence, assumptions, forecast history, invalidation risks, peer forecast compare.

## Success criteria

| Metric | Target |
|---|---|
| Module / scenario / confidence coverage | >95% |
| Explainability | 100% |
| History retention / accuracy tracking | 100% |
| Probability validation | 100% |
| Unsupported forecasts / BUY-SELL | 0 |

## Tests

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest forecast_intelligence_engine/tests/test_fie.py -q
```
