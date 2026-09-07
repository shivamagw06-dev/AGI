# Institutional Reasoning Audit Engine (IRAE) V1

**Programme:** RQ2 — Institutional Reasoning  
**Sprint:** 10 (final)  
**Architecture:** v1.0.1 LOCKED — final certification gate, not a top-level layer

## Position

```
Institutional Decision Readiness Engine
        ↓
IRAE (Reasoning Certification)
        ↓
Investment Committee
```

## Primary question

> Did AGIB reason correctly?

## Audit dimensions

Evidence Traceability · Logical Consistency · Assumption Quality · Contradiction Handling · Confidence Calibration · Policy Compliance · Analyst Scope · Reasoning Completeness

## Certification states

`PASS` · `PASS WITH OBSERVATIONS` · `REVIEW REQUIRED` · `FAIL`

## Reasoning Replay Engine

IRAE reconstructs an 11-step deterministic replay:

`Question → Hypothesis → Research Questions → Evidence → Testing → Falsification → Belief Update → Investment Thesis → Debate → Decision Readiness → Reasoning Audit`

Replay supports play, pause, step forward/back and restart. It is suitable for debugging, analyst training, user explanation, ILM outcome learning and IRS regression diagnosis.

## Admin

`/admin/reasoning-audit`
