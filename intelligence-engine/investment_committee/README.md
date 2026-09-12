# Investment Committee Intelligence (ICI V1)

Pure intelligence orchestration. **Not an engine.**

No new data. No provider changes. No UI redesign.

## Flow

```text
9 Analyst Opinions
  → Consensus Engine
  → Conflict Engine
  → Evidence Challenge
  → Confidence Recalibration
  → Committee Vote
  → Committee Minutes (stored)
  → Minority Opinions
  → Historical Memory / Prediction Accountability
  → Committee Decision (vote, not Buy/Hold/Sell)
  → CIO
```

## Internal objects

CommitteeConsensus · CommitteeConflict · CommitteeQuestion · CommitteeChallenge ·
CommitteeVote · CommitteeMinutes · CommitteeDecision · CommitteeAccuracy ·
MinorityOpinion · OpenEvidenceRequest

## Soft-wire

Called from Institutional Analyst Framework committee aggregation when
`investment_committee_intelligence` + `ask_agi_ici` are enabled.
