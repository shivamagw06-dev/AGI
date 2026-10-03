# Institutional Thesis Construction Engine (ITCE) V1

**Programme:** RQ2 — Hypothesis Intelligence  
**Sprint:** 7  
**Architecture:** v1.0.1 LOCKED — soft-wire only; not a top-level intelligence layer

## Position

```
Bayesian Belief & Confidence Engine
        ↓
ITCE (Thesis Construction)   ← this package
        ↓
Investment Committee
```

## Primary question

> What is the strongest institutional investment thesis supported by the evidence?

## Thesis structure

Core Thesis · Supporting Pillars · Contradictions · Catalysts · Risks · Disconfirming Evidence · Confidence · Timeline

## Pillars

Business Quality · Financial Quality · Capital Allocation · Competitive Position · Valuation · Macro Alignment · Portfolio Fit

Dependency chain: `Business Quality → Financial Quality → Valuation → Portfolio Fit` (weak upstream pillars discount downstream confidence and raise a Committee notification).

## Quality rules

≥4 supporting pillars · ≥2 major contradictions · ≥3 catalysts · ≥1 thesis-breaking condition

## Committee intelligence extensions

- **Pillar Interaction Matrix** — directed quantified influence (for example Business `+0.60` → Financial, Financial `+0.40` → Valuation)
- **Thesis Stability** — Stable / Improving / Weakening / Volatile across prior snapshots
- **Thesis Quality** — evidence, contradiction handling, coverage, calibration, completeness and coherence; separate from conviction
- **Investment Narratives** — one-sentence, one-paragraph and one-page representations from the same thesis object
- **Thesis DNA** — durable company traits and current alignment fingerprint
- **Conviction Waterfall** — exact additive explanation of final conviction
- **Monitoring Dashboard** — current value, breaking threshold, distance and state per pillar
- **Thesis Evolution** — versioned ILM-ready history
- **Thesis Pressure Gauge** — Low / Moderate / High / Critical pressure independent of confidence

## Admin

`/admin/thesis-construction`
