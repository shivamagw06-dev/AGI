# IDS-01 — Institutional Decision System

**Mission:** AGI makes **explicit, auditable institutional decisions**. Reports only render them.

```text
Evidence → Reasons → Decision System → Institutional Report
```

No Gemini. No GPT. No phrase bank.

## InstitutionalDecision (immutable + versioned)

```text
decision_id
decision_version
generated_at
reason_version
report_version
evidence_snapshot_id
recommendation / conviction / confidence / horizon
supporting_reasons / contradicting_reasons / unknowns
upgrade_conditions / downgrade_conditions / monitoring_items
decision_graph
```

## Deterministic rules (transparent score)

| Factors | Recommendation |
| --- | --- |
| Strong/Excellent BQ + Strong FQ + Cheap + Low risk | BUY |
| Strong stack + Fair + Moderate risk | HOLD |
| Weak + Weak + Expensive + High risk | SELL |

Exact scoring is encoded in `decision_engine.py` (`rule_path` stored on every decision).

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_decision --ticker AXISBANK
PYTHONPATH=. python3 -m institutional_decision --ticker AXISBANK --include-history
```

API:

- `GET /v1/decision/health`
- `POST /v1/decision/company`
- `GET /v1/decision/company/{ticker}?include_history=true`

BFF: `/api/intelligence/decision/*`

## Report integration

`compose_report()` calls IDS, then renders the `InstitutionalDecision`.  
Fixture recommendation fields are **not** the source of truth.

## Calibration (IDS-02)

After IDS-01 produces a decision, IDS-02 computes calibrated confidence from a versioned `CalibrationProfile`. See `docs/AGI_IDS_02_DECISION_CALIBRATION.md`.

## Out of scope

Phrase bank, grammar engines, LLM polish, market/portfolio/macro decisions.
