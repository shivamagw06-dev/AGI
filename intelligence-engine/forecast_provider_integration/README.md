# Forecast Provider Integration (FPI)

India-first provider architecture for the Forecast Intelligence Platform.

## Principle

> External providers supply raw market information. The Knowledge Platform transforms it into institutional knowledge. Forecast Intelligence never reasons over raw APIs—it reasons over AGI's knowledge base, enriched with a fresh live market snapshot when required.

## Priority

1. **Groww** — primary live market (LTP, OHLC, depth, VWAP, WS)
2. **Yahoo Finance** — fundamentals, statements, research, history
3. **NSE** — disclosures / bhavcopy
4. **BSE** — corporate actions
5. **Company IR** — official documents

## Controlled refresh on forecast path

```text
Company Knowledge → Market Snapshot → If stale → Refresh Live Snapshot → Continue Forecast
```

No other external provider calls inside the forecasting pipeline.

## APIs

```text
GET  /v1/forecast/providers/health
GET  /v1/forecast/providers/dashboard
POST /v1/forecast/providers/publish/{entity}
POST /v1/forecast/providers/snapshot/{entity}
GET  /v1/forecast/providers/company/{entity}
GET  /v1/admin/forecast-providers
```

## Traces

`groww_market_refresh` · `yahoo_financial_refresh` · `forecast_bundle_generation` · `forecast_market_snapshot` · `provider_failover` · `knowledge_refresh`
