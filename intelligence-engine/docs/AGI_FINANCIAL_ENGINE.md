# AGI Financial Engine (AFE)

AFE is AGI's canonical deterministic calculation facade. It extends the existing Financial Statements Engine formula registry, warehouse lineage, valuation engine, and governed tool runtime; it does not create a second financial store.

## Architecture audit

- Existing canonical financial facts: `financial_statements_engine` and its financial warehouse.
- Existing derived formulas: safe AST registry under `derived_metrics/formula_registry`.
- Existing valuation: `valuation_engine`.
- Existing scenarios and sensitivities: `forecast_intelligence`.
- Existing provenance: CFDM facts, evidence references, warehouse lineage and PIT views.
- Existing governed tool: `CALCULATE`; AFE supplies its previously missing bound handler.

## Implemented registry

The first production registry contains 22 calculations across basic mathematics, returns, time value, profitability, banking, bank valuation, valuation and telecom scenarios. Every record exposes an ID, version, formula, required inputs, output unit and methodology.

Key bank calculations: ROA, ROE, loan growth, deposit growth, CASA ratio, credit-deposit ratio, GNPA, NNPA, PCR, NIM, credit cost, CET1, CRAR, cost-to-income, P/B and justified P/B.

## Input contract

Inputs may be numbers or evidence objects:

```json
{
  "value": 100,
  "unit": "INR million",
  "currency": "INR",
  "period": "FY2026",
  "source_id": "filing:pat:FY2026",
  "available_at": "2026-05-01"
}
```

AFE rejects missing inputs, mixed units, mixed currencies, mixed periods, zero denominators, unsupported calculations, invalid terminal assumptions, and point-in-time violations. It never executes model-provided formulas or arbitrary code.

## Tool contract

```json
{
  "tool": "CALCULATE",
  "operation": "ROE",
  "inputs": {
    "pat": 100,
    "opening_equity": 600,
    "closing_equity": 650
  }
}
```

The result includes raw and display values, formula/version, inputs, provenance, sources, assumptions, validation, warnings, timestamp and execution time.

## Current acceptance status

- Deterministic registry and executor: implemented.
- Banking calculation set needed for HDFC analysis: implemented.
- Governed `CALCULATE` binding: implemented.
- Unit, currency, period and PIT validation: implemented.
- Financial Data Resolver: implemented against the canonical Financial Statements Engine, with a fallback through the Institutional Warehouse's published annual-financial read API. It applies bank-specific mappings, source precedence, conflict exposure, unit normalization, staleness and PIT controls; unsupported inputs remain unavailable rather than estimated.
- Company-aware `CALCULATE`: implemented. Requests may provide company, calculation, period and as-of date; the model does not supply warehouse numbers.
- HDFC banking bundle: ROE, loan/deposit growth, NIM, GNPA, NNPA, PCR, credit cost, CET1, CRAR and P/B resolve through the bridge when canonical facts exist.
- Ask planning: investment and banking questions now select `GET_FINANCIALS` and `CALCULATE`; client-response composition of a complete multi-metric bundle remains a separate reasoning integration gate.
- DCF, IRR/XIRR, portfolio return analytics, full peer/reverse-DCF, insurance/NBFC/manufacturing/FMCG/IT formula expansion: pending registry expansion.
- Current tests cover registry integrity, ROE/provenance, banking, telecom scenario, failure states, unit/PIT checks and governed execution.

Do not claim the entire specification complete until the remaining formula families and end-to-end HDFC warehouse acceptance test pass.
