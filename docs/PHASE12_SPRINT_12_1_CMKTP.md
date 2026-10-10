# Phase 12 — Sprint 12.1: Continuous Market Knowledge Platform (CMKTP)

**Status:** Implemented in `intelligence-engine/continuous_market_knowledge/`  
**Version:** 0.1.0  
**Pattern:** Market twin of CSKP / Macro CMKP  
**Note:** Programme short is **CMKTP** to avoid collision with Continuous Macro Knowledge (**CMKP**).

---

## Objective

Continuously acquire, validate, normalize and publish institutional **Market Knowledge Objects** describing the current state of financial markets.

CMKTP is **not a market data service**. It transforms live market tips into higher-order institutional knowledge that downstream reasoning systems consume. User requests never trigger collection.

---

## Architecture

```text
Groww (ops Indian live) · Yahoo (ops global)
        │
Macro / Sector / Company Intelligence (soft)
        │
        ▼
Market Intelligence Builder
        │
Validation → Normalization → Materiality → Learning → Publication
        │
Market Knowledge Store → CMKTP_KRIG → Intelligence Engine / Investment Office
```

---

## Market domains

`india_equity` · `global_equity` · `breadth` · `liquidity` · `volatility` · `institutional_flows` · `leadership` · `cross_asset` · `risk_sentiment` · `market_health`

Higher-order concepts (regime, breadth, liquidity, leadership, risk sentiment, health) are **derived internally**, not fetched as conclusions from external providers.

---

## Guardrails

* Ask never collects or constructs
* `providers_queried` always `[]` on read paths
* Groww / Yahoo reserved for ops collection — never on Ask
* Only material changes trigger learning / research refresh signals
* No BUY/SELL or target prices

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/cmktp/health` | Programme health |
| GET | `/v1/market` | Composite Market Knowledge Object |
| GET | `/v1/market/dashboard` | Mission Control board |
| GET | `/v1/market/regime` | Current regime |
| GET | `/v1/market/breadth` | Breadth metrics |
| GET | `/v1/market/liquidity` | Liquidity |
| GET | `/v1/market/leadership` | Sector/stock leadership |
| GET | `/v1/market/flows` | Institutional flows |
| GET | `/v1/market/volatility` | Volatility |
| GET | `/v1/market/health` | Market health score |
| POST | `/v1/market/run` | Ops rebuild only |
| GET | `/v1/admin/market-operations` | HTML ops board |

---

## LangSmith traces

```text
market_collection
market_validation
market_normalization
market_materiality
market_learning
market_publication
market_retrieval
```

---

## Mission Control

**Market Intelligence Operations** board (`phase: 12.1`):

* Current Market Regime · Market Health Score · Breadth · Liquidity · Flows · Leadership · Cross-Asset · Risk Sentiment · Material Events · Freshness · Collection / Publication status

---

## Soft consumers

* **IFI** soft-reads CMKTP for market intelligence (`CMKTP_KRIG`)
* **CSKP** soft-reads CMKTP for market tips when published

---

## Success criteria

* Market Knowledge Objects generated from ops Groww/Yahoo tips + AGIB Company/Sector/Macro soft inputs
* Higher-order concepts derived internally
* Only material changes trigger learning
* Published knowledge available via store for Ask/IFI without live feeds

---

## Phase 12 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 12.1 | CMKTP | Continuous Market Knowledge Platform |
| ✅ 12.2 | HMKIP | Historical Market Intelligence Platform |
| ✅ 12.3 | MKRI | Market Relationship Intelligence |
| ✅ 12.4 | HMKAI | Historical Market Analogue Intelligence |
| ✅ 12.5 | MKFI | Market Forecast Intelligence |
