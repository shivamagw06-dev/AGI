# AGI v4.0 — Institutional Investment Office — COMPLETE

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
FOUNDATION: AGI v3.6 Institutional Judgment (FROZEN)
STATUS: COMPLETE after Sprint 5.5
DATE: 2026-07-28
```

## Architecture (frozen at v4.0)

```text
Research Office
        │
        ▼
Investment Office
        │
 ┌──────┼────────┐
 ▼      ▼        ▼
Thesis Decision Portfolio
        │
        ▼
Monitoring
        │
        ▼
Learning
```

| Sprint | Module | Object |
|--------|--------|--------|
| 5.1 | Investment Thesis (ITE) | Why interesting? |
| 5.2 | Decision Office (IDO) | What governance action? |
| 5.3 | Portfolio Office (IPO) | How does it compare? |
| 5.4 | Monitoring Office (IMO) | What changed? |
| 5.5 | Learning Office (ILO) | What should we remember? |

**No Sprint 5.6.** No further Office modules in this release train.

## Evaluation stack (complete)

```text
IEL → HQS → CQS → CFQS → ITQS → DQS → PQS → MQS → LQS
```

All Phase 4/5 quality scores are independent of CIO / `DIMENSION_WEIGHTS`.

## Hard separations preserved

* Analysis ≠ Decision ≠ Execution  
* Portfolio Ideas ≠ Positions  
* MonitoringEvents recommend review — they do not mutate history  
* Learning = process memory — not Knowledge Factory market facts  
* `allow_positions = false`

## Post-v4.0 focus (production cycle)

Do **not** invent new conceptual Office layers. Instead:

1. **Live data** — LIDI certification; controlled provider integrations  
2. **Performance** — latency, caching, end-to-end response times  
3. **UI/UX** — theses, decisions, portfolio ideas, monitoring events, learnings as first-class entities  
4. **Real-world validation** — run alongside human research; compare outcomes  
5. **Continuous evaluation** — keep IEL + independent scores on every meaningful change  

## Verdict

Phases 1–4 answered: *Can AGI understand and evaluate investments?*  
Phase 5 answered: *Can AGI organise and manage investment work over time?*

**AGI v4.0 Investment Office architecture is complete.**
