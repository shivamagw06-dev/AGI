# Sprint 6.5 — Operate: AKO + KFE + KCE

## Mission

Close Phase 6 with a production-ready **continuous knowledge operating system**:

```text
Acquire → Structure → Learn → Serve → Operate
  6.1      6.2        6.3     6.4     6.5
```

Sprint 6.5 is one coherent Operate sprint:

1. **AKO** — Adaptive Knowledge Orchestrator  
2. **KFE** — Knowledge Freshness Engine  
3. **KCE** — Knowledge Confidence Engine  

```text
AGI should continuously learn from the market,
not continuously research for the user.
```

## Contracts

- `knowledge-platform/docs/AKO_PLATFORM_CONTRACT.md`
- `knowledge-platform/docs/KFE_KCE_OPERATE_CONTRACT.md`

## What shipped

### AKO
- Market sessions, adaptive schedules, event boosts, overnight rebuilds
- Retry / backoff / DLQ, Mission Control telemetry
- Primary orchestrator (`KAIP_AKO=true`)

### KFE
- Per-object freshness: age, `Fresh` / `Needs Refresh`, `current_as_of`
- `freshness_registry` written on publish
- KRIG bundle freshness + overnight / Mission Control portfolio health

### KCE
- Multi-source confidence scores (e.g. financials ~99% when Yahoo+NSE+IR agree; news ~58% single Yahoo)
- `confidence_registry` written on publish
- KRIG bundle confidence for IE evidence weighting before IEW

## Ask separation

```text
User Question → KRIG (freshness + confidence) → Judgment → Answer
```

Collectors remain background-only. Freshness “Needs Refresh” is an ops signal for AKO — not an Ask trigger.

## Verification

```bash
cd knowledge-platform && pytest -q
```

## Phase 6 complete when

- Continuous ingestion ✔  
- Continuous learning ✔  
- Continuous updating ✔  
- Continuous publishing ✔  
- Continuous retrieval ✔  
- Freshness + confidence on every KO ✔  

Next: Phase 7 research-generation capabilities against this continuously refreshed knowledge base.
