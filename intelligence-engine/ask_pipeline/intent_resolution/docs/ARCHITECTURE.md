# Ask Pipeline 2.0 — Intent Resolution Layer (Track A)

```
Question
  → Language Analysis
  → Intent Classification
  → Entity Detection (Concept Mode when unbound)
  → Temporal Detection
  → Question Type
  → Evidence Requirements
  → IERE
```

Soft-wire only. Knowledge Factory and governance internals remain frozen.

## Guarantees

- "Why / explain / how would you" never forced onto valuation contracts
- No entity → Concept Mode (never invent Infosys)
- `as_of` / FY / before COVID inherited by IERE
- Historical replay routed as `HistoricalReplay`
