# IFSE Architecture

```text
Question + Intent + Entities + Answer Assembly
  → Sector / keyword detection
  → Sector framework composition
  → Intent / question-type overlays
  → Forbidden rejection
  → Replay filter (available_from ≤ as_of)
  → Confidence
  → Framework Explanation Object
  → Validation gates
  → Soft-wire to Ask packs / RO publications
```

Deterministic. Multi-framework. No LLM. Reasoning frozen.
