# Bayesian Belief & Confidence Engine (BBCE) V1

**Programme:** RQ2 — Hypothesis Intelligence  
**Sprint:** 6  
**Architecture:** v1.0.1 LOCKED — soft-wire only; not a top-level intelligence layer

## Position

```
Institutional Falsification Engine
        ↓
BBCE (Belief Update)   ← this package
        ↓
Business / Financial / Valuation opinions
```

## Primary question

> Given all available evidence, what should AGIB currently believe, and how confident should it be?

## Update rule

```
logit(posterior) = logit(prior) + Σ log LR(evidence effects, falsification)
```

Confidence is calibrated separately from belief probability.

## Belief states

Strongly Supported · Supported · Leaning Positive · Neutral · Leaning Negative · Challenged · Contradicted · Rejected

## Admin

`/admin/belief-engine`
