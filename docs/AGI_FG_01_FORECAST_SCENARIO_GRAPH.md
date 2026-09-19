# FG-01 — Forecast & Scenario Graph

**Mission:** AGI evaluates **deterministic future scenarios** by propagating explicit assumptions through the Institutional Knowledge Graph. This is not price prediction.

```text
Evidence → Knowledge Graph → Scenario Engine → Forecast Graph → Inference → Decision → Calibration → Report
```

No ML. No Monte Carlo. No LLM.

## ForecastScenario

Immutable, versioned object with:

- explicit `probability`
- `assumptions[]`
- `changed_nodes` / `propagated_impacts`
- `resulting_decision` / `resulting_confidence`
- forecast graph, sensitivity, diagnostics, lineage

## Propagation example

```text
Repo Rate ↓ → NIM ↑ → Profitability ↑ → ROE ↑ → Business Quality ↑ → Decision score ↑
```

## Standard scenarios

| Scenario | Default probability |
| --- | --- |
| Base | 50% |
| Bull | 25% |
| Bear | 25% |
| Stress / Optimistic | explicit when requested |

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_forecasting --ticker AXISBANK --scenario bull
PYTHONPATH=. python3 -m institutional_forecasting --ticker AXISBANK --scenario all
```

API:

- `GET /v1/scenario/health`
- `POST /v1/scenario/company`
- `GET /v1/scenario/company/{ticker}?include_graph=true&include_propagation=true`

## UI

Company workspace → **Forecast** tab: Base / Bull / Bear / Stress, comparison, propagation, sensitivity.

## Out of scope

ML price prediction, Monte Carlo, portfolio-wide scenarios, cross-company contagion, phrase banks, LLM.
