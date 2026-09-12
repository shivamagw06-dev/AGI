# IO-01 — Institutional Observation Engine

**Mission:** Transform continuous gather from a passive data pipeline into **proactive institutional awareness**. AGI detects meaningful changes, classifies significance with hysteresis, updates knowledge, re-evaluates decisions when required, and emits structured observations with full lineage.

```text
Continuous Gather
↓
Observation Engine
↓
Knowledge Graph Updated
↓
Decision Re-evaluated (when required)
↓
Calibration Updated
↓
Alerts
↓
Report Updates (when required)
```

No Gemini. No GPT. No natural-language rewriting. No predictive alerts.

## InstitutionalObservation

Immutable, versioned first-class object alongside Evidence, Knowledge, Reasons, Decisions, Calibration, Forecasts, and Reports.

Fields include: `observation_id`, `company`, `timestamp`, `category`, `severity`, `confidence`, `summary`, `evidence_snapshot_id`, affected entities/reasons/decisions/forecasts, `requires_review`, `recommended_action`, plus diagnostics and lineage.

## Categories

Quarterly Results · Management Commentary · Corporate Actions · Shareholding · Regulation · Macro · Valuation · Forecast · Risk · Governance · Sector · News · Market Structure

## Hysteresis (alert fatigue control)

Configurable `HysteresisProfile` (default):

| Gate | Default | Effect |
| --- | --- | --- |
| Valuation change | &lt; 2% | Silent graph update |
| Confidence change | &lt; 1 point | No decision update |
| Forecast revision | &lt; materiality threshold | Silent graph update |
| High / critical severity | always | Emit observation + downstream workflows |
| Recommendation change | always material | Observation + recompute |

Share split → observe optionally, **no** recommendation recompute.  
Large earnings revision → recompute graph → reasons → decision → calibration.

## Package

`intelligence-engine/institutional_observation/`

| Module | Role |
| --- | --- |
| `detector.py` | New / changed / removed evidence, valuation, macro, forecast |
| `classifier.py` | Category, priority, severity, confidence |
| `significance.py` | Materiality + hysteresis gates |
| `impact.py` | Affected companies, graph nodes, reasons, decisions, forecasts |
| `evaluator.py` | Recommended actions + deterministic decision re-eval |
| `scheduler.py` | Watchlist-priority observation cycles |
| `notifier.py` | Structured alerts (no LLM) |
| `diagnostics.py` | Quality gates |
| `production.py` | Observe / inject / Mission Control Observation Center |

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_observation --ticker AXISBANK
PYTHONPATH=. python3 -m institutional_observation --ticker AXISBANK --inject quarterly_results
PYTHONPATH=. python3 -m institutional_observation --ticker AXISBANK --inject rbi_repo_cut
```

API:

- `GET /v1/observation/health`
- `GET /v1/observation/company/{ticker}?critical_only=true&include_decision_changes=true`
- `POST /v1/observation/company`

BFF: `/api/intelligence/observation/*`

## UI

Company workspace → **Observations** tab: timeline, severity, evidence, decision changes, recommended actions.

Mission Control → **Observation Center** soft slice: today's observations, critical, decision changes, pending reviews, latency, throughput.

## Quality gates

Reject observation if missing: evidence, severity, impact, lineage, recommendation, or diagnostics.

## Out of scope

LLM summarization · portfolio-wide optimization · cross-market contagion · NL rewriting · predictive alerts
