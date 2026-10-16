# AGIB v3.4 Track A — Ask Pipeline 2.0 (Intent Resolution)

## Goal

Ensure every question reaches the correct execution path **before IERE**.

## Flow

```
Question → Language → Intent → Entities → Temporal → Question Type → Evidence Requirements → IERE
```

## Exit gates (measured)

| KPI | Result |
|-----|--------|
| CIO routing accuracy (25 gold labels) | **100%** |
| Historical routing | **100%** |
| Entity pollution on concept questions | **0%** |
| Forbidden valuation qtype on explain/why | **0** |

Legacy `classify_question` alone mis-typed several CIO explain/why prompts as `valuation` / `investment_decision`.

## Soft-wires

- `ask_pipeline/intent_resolution/` — new layer
- `ask_pipeline/pipeline.py` — IRL before knowledge/IERE; overrides `classify_question`
- `ask_pipeline/policy.py` — concept / explain / historical-replay skip live IE packs
- `ask_pipeline/knowledge.py` — concept mode + as_of replay
- `govern_answer(..., question_type_override=)` — soft hook only

Knowledge Factory untouched. No new intelligence domains.
