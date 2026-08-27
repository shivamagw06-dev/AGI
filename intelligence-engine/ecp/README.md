# ECP V1 — Evidence Completion Pipeline

**Architecture status:** v1.0.1 LOCKED  
**Role:** Orchestration layer (not an engine, not a recommendation model)

```
Question → CID → Evidence Quality Check → Identify Missing → ECP
  → Update LEO → Update CID → Re-evaluate Gates → IRP → Answer
```

## Behaviour

1. Ask AGI still **refuses** recommendations when evidence is insufficient.
2. Before the gate evaluation, ECP determines **why** evidence is missing.
3. ECP auto-retrieves validated gaps via MarketDataClient / DVC / Yahoo / KIP / KF.
4. Never overwrites higher-confidence data — fill empties only.
5. If still insufficient, explain exactly what is missing to reach Institutional Grade.

## Flags

| Env | Default | Purpose |
|-----|---------|---------|
| `ECP` | `true` | Master enable |
| `ECP_BEFORE_IRP` | `true` | Complete before IRP |
| `ECP_BEFORE_GATE` | `true` | Second soft pass before final gate |

## Admin

`/admin/evidence-completion` — coverage, completed automatically, still missing, providers, conflicts, quality improvement.

## Out of scope

No LEO / IRP / RSP redesign. Recommendation gate logic unchanged.
