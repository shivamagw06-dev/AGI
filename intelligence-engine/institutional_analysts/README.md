# Institutional Analyst Framework (IAF V1.1)

Answer Construction orchestration only. **Not an engine.**

## Locked architecture

Does **not** redesign CID, LEO, IRP, Company Analysis, Financial Intelligence,
Company Monitor, Knowledge Foundation, Academy, DVC, ECP, MarketDataClient, or providers.

No new data. No new intelligence. Ownership of existing intelligence only.

## Flow

```text
Question
  → Research Planner (assigns mandates)
  → 9 Specialist Analysts (structured opinions + memory)
  → Investment Committee meeting
        Stage 1 Consensus
        Stage 2 Conflicts
        Stage 3 Missing Evidence
        Disagreement Matrix + Minutes
  → Chief Investment Officer (editor)
  → Institutional Report
```

## Analyst contract

Each analyst has mandate metadata:

- Mandate
- Primary Question
- Primary Inputs
- Outputs
- Never (out-of-domain)

Each opinion is a **structured object**:

```json
{
  "summary": "...",
  "stance": "Bullish|Neutral|Bearish",
  "strengths": [],
  "weaknesses": [],
  "evidence": [],
  "unanswered_questions": [],
  "confidence": {
    "evidence": 0.0,
    "knowledge": 0.0,
    "freshness": 0.0,
    "coverage": 0.0,
    "overall": 0.0
  },
  "what_changed": null
}
```

Domain guards strip out-of-mandate vocabulary (e.g. Business never discusses PE).

## Committee

Soft-calls **Investment Committee Intelligence (ICI V1)** for full deliberation:

1. Consensus Engine
2. Conflict Engine
3. Evidence Challenge
4. Confidence Recalibration
5. Committee Vote
6. Committee Minutes (stored)
7. Minority Opinions
8. Historical Memory / Prediction Accountability
9. Recommendation as vote (not Buy/Hold/Sell)

## CIO

Editor, not summariser:

- Never repeats analyst wording
- Never names engines / providers / subsystems
- Writes institutional prose from committee signals / vote only

## Flags

`institutional_analysts`, `ask_agi_iaf` (+ ICI: `investment_committee_intelligence`, `ask_agi_ici`)
