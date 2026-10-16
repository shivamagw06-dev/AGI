# Phase 9 — Sprint 9.2: Institutional Scenario Intelligence (ISI)

**Status:** Implemented in `intelligence-engine/institutional_scenario_intelligence/`  
**Version:** 0.1.0  
**Depends on:** Sprint 9.1 IFI Forecast Bundles  
**Out of scope:** Probabilities (9.4 PCI), catalyst trigger lifecycle (9.3 CTI), forecast validation learning (9.5)

---

## Naming

Not a “Forecast Engine.”  
**Institutional Scenario Intelligence (ISI)** — Investment Committee style evaluation of **plausible outcomes**.

---

## Philosophy

Institutional investors ask: **What are the plausible outcomes?** — not “What will happen?”

```text
IFI Forecast Bundle
        │
        ▼
ISI → Bull / Base / Bear
        │
        ▼
Scenario Comparison + Contradictions
        │
        ▼
Scenario Report → Investment Office
```

---

## Rules

- Consumes **only** Forecast Bundles (+ embedded knowledge)  
- Every scenario cites current, historical and research evidence  
- Contradictions are **preserved**, not discarded  
- No BUY / SELL / target prices  
- No probabilities until PCI (9.4)  
- No live Yahoo / NSE calls  

---

## APIs

```text
GET  /v1/scenarios/company/{ticker}
GET  /v1/scenarios/sector/{sector}
GET  /v1/scenarios/market
GET  /v1/scenarios/macro
POST /v1/scenarios/report
GET  /v1/scenarios/dashboard
```

---

## Success path — Infosys

```bash
curl 'http://127.0.0.1:8000/v1/scenarios/company/INFY'
```

Returns Bull (AI / large deals / margin recovery), Base (near guidance), Bear (US demand / pricing / margin compression) with comparison and contradiction analysis.

---

## Phase 9 roadmap

| Sprint | Module | Purpose |
|---|---|---|
| ✅ 9.1 | IFI | Forecast-ready knowledge bundles |
| ✅ 9.2 | ISI | Bull / Base / Bear evaluation |
| ➡️ 9.3 | CTI | Events that move scenarios |
| 9.4 | PCI | Probabilities & confidence |
| 9.5 | FVL | Forecast vs outcome learning |
