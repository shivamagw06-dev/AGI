# Investment Intelligence Engine (IIE) v1.0

Transforms **verified EVE evidence** into reusable institutional investment intelligence.

## Position

```text
AOI → EVE → KCV → KF → IIE → KIP → IRP → RSP → Ask AGI
```

Architecture **v1.0.1 LOCKED**. IIE extends only via soft integration points — no redesign of KF1, KCV1, AOI, EVE, KIP, IRP, RSP, or Ask AGI.

## Mission

Answer: **"What does this mean for an investor?"**

Never hallucinate. Consume only verified/pending EVE evidence (optional KF/KC enrichment). Version all analytical outputs; never overwrite history.

## Objects

Company Intelligence Profile · Company DNA · Sector · Theme · Macro Impact · Catalyst · Risk · Opportunity · Scenario Set · Investment Thesis · Monitoring Checklist · Relationship · Comparison · Evolution History

## APIs

`/v1/iie/health` · `/dashboard` · `/analyse` · `/company/{key}` · `/sector` · `/theme` · `/thesis` · `/scenario` · `/catalysts` · `/risks` · `/opportunities` · `/compare` · `/monitor` · `/dna` · `/macro` · `/evolution` · `/search` · `/consult` · `/batch`

## Ask AGI

Soft field `investment_intelligence` on SearchView via `IieService.consult` — retrieve structured intelligence **before** reasoning.

## Out of scope (v2/v3)

Valuation engines, autonomous agents, conviction scoring — not implemented in v1.
