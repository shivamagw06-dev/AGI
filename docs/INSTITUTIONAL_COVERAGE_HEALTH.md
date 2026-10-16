# Institutional Coverage Health v1.0

**Engine:** `institutional_coverage_health`  
**Primary KPI:** Valuation applicability coverage (VPAE-aligned)

## Why

Do **not** use this as the primary platform KPI:

```text
Coverage = (PE OR Upstox ratios) / company_master
```

That mixes **data availability** with **valuation applicability**. A bank, REIT, ETF, or loss-making company may correctly lack a usable P/E without being “uncovered.”

## Definition

```text
Coverage =
  Companies with a valid valuation methodology
  and sufficient supporting data
  ÷
  Companies expected to have a valuation model
```

`NOT_APPLICABLE` instruments are excluded from the denominator.

| Category | Counted as covered? | Reason |
| --- | --- | --- |
| Profitable IT with P/E | Yes | Primary model available |
| Bank with P/B + ROE | Yes | Primary model available |
| Loss-making SaaS with EV/Sales | Yes | Appropriate model available |
| REIT with AFFO/PNAV | Yes | Appropriate model available |
| ETF valued by NAV | Yes | Appropriate model available |
| Missing all valuation inputs | No | Insufficient data |
| Unresolved ISIN / provider gaps | No | Incomplete ingestion |

## Five layers

1. **Universe** — company master vs tracked
2. **Data** — profile, statements, ownership, price, corporate actions, key ratios
3. **Valuation** — valid VPAE primary model (primary KPI)
4. **Metric** — PE / PB / ROE / ROCE / EV/EBITDA / EV/Sales / dividend yield presence
5. **Intelligence** — HVIE percentile/bands/regime, VARIE/research, confidence

## Dashboard payload

`GET /v1/valuation/coverage/health` returns:

- `dashboard` — Universe / Raw Data / Valuation / Historical Intelligence / Research Intelligence / DQIV bars
- `valuation_coverage` — covered / expected / by primary model / missing reasons
- `data_coverage`, `metric_coverage`, `intelligence_coverage`
- `research_coverage` — research ready + needs statements/history/ratios/review
- `residual_gap` — missing ISIN / no fundamentals / provider failure / delisted

Live Upstox bootstrap queue (Pending / Retry / Failed / ETA) remains on:

- `GET /api/market/upstox-bootstrap/status`

## VPAE integration

Unavailable metrics are not treated as missing coverage when a valid primary model exists:

```text
PE → Unavailable (negative earnings)
Primary Model → EV/Sales
Coverage → Complete
```

## Market snapshot

`GET /v1/valuation/market` now reports:

- `coverage_pct` / `valuation_coverage_pct` — VPAE applicability
- `legacy_pe_or_provider_coverage_pct` — diagnostic only

## UI

Valuation Research Workspace home (`/admin/valuation-terminal`) shows the Coverage Health panel between the market snapshot and sector directory.

## Architecture

```text
Warehouse → VPAE + HVIE + ratios → Institutional Coverage Health → BFF → UI
```

No UI vendor calls. No UI valuation calculations. Analysis language only.
