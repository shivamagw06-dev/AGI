# Phase 9 — Forecast Intelligence Platform (Provider Integration)

**Status:** Implemented in `intelligence-engine/forecast_provider_integration/`  
**Version:** 0.1.0  
**Depends on:** IFI Forecast Bundles, Knowledge Platform collectors, Node Groww (optional live)

---

## Architectural principle

> External providers supply raw market information. The Knowledge Platform transforms it into institutional knowledge. Forecast Intelligence never reasons over raw APIs—it reasons over AGI's continuously maintained knowledge base, enriched with a fresh live market snapshot when required.

Forecast Intelligence must **never become a data collector**.

---

## Provider priority (India-first)

| Priority | Provider | Role |
|---|---|---|
| 1 | **Groww** | Primary live market (LTP, OHLC, depth, VWAP, WS) |
| 2 | **Yahoo Finance** | Fundamentals, statements, research, history |
| 3 | **NSE** | Official disclosures / bhavcopy |
| 4 | **BSE** | Corporate actions |
| 5 | **Company IR** | Official documents & presentations |

Groww is **not** used for financial statements or analyst estimates.  
Yahoo is **never** polled every few seconds.

---

## Static vs dynamic knowledge

Every Company Knowledge object has two layers:

- **Static** — profile, statements, historicals, ownership, analogues (Yahoo / IR / NSE / BSE)
- **Dynamic market state** — live price, OHLC, volume, VWAP, bid/ask, depth (Groww; Yahoo fallback)

---

## Controlled refresh on the forecast path

```text
Company Knowledge
        │
        ▼
Market Snapshot
        │
        ▼
If stale (default 60s)
        │
        ▼
Refresh Live Snapshot (Groww → Yahoo failover)
        │
        ▼
Continue Forecast Bundle
```

No other external provider calls are allowed inside the forecasting pipeline.

---

## Soft wire into IFI

`InstitutionalForecastEngine` enriches retrieved catalog knowledge via
`forecast_provider_integration.bridge.enrich_forecast_inputs`.

- Bundle `providers_queried` remains `[]`
- Provenance records `controlled_refresh=market_snapshot_when_stale`
- Live snapshot appears under `market_intelligence.live_snapshot` and layered `current_knowledge`

---

## APIs

```text
GET  /v1/forecast/providers/health
GET  /v1/forecast/providers/dashboard
GET  /v1/fpi/health
POST /v1/forecast/providers/publish/{entity}
POST /v1/forecast/providers/snapshot/{entity}
GET  /v1/forecast/providers/company/{entity}
GET  /v1/admin/forecast-providers
```

---

## LangSmith traces

`groww_market_refresh` · `yahoo_financial_refresh` · `forecast_bundle_generation` · `forecast_market_snapshot` · `provider_failover` · `knowledge_refresh`

---

## Mission Control

Provider Health dashboard shows Groww / Yahoo / NSE / BSE / Company IR status, snapshot freshness, knowledge freshness, and failover events. Soft-wired into Mission Control `api_status` and institutional intelligence board.
