# Sprint 6.2 — Institutional Knowledge Objects (IKO)

## Goal

Convert raw market data into **institutional knowledge**.

Not JSON. Not API responses. Knowledge.

## Contract

Authoritative: [`knowledge-platform/docs/IKO_PLATFORM_CONTRACT.md`](../knowledge-platform/docs/IKO_PLATFORM_CONTRACT.md)

## What changed vs 6.1

| 6.1 | 6.2 |
|---|---|
| Acquire + canonicalize | Define what AGI learns |
| Five KO types | Ten universal IKO types |
| Flat payloads | Institutional sections (Business, Valuation, Growth, …) |
| Basic learning deltas | Learning Events with Category / Importance / Affected |
| Publish KOs | Publication envelope: Company → Sector → Market → Evidence Graph → Memory |

## Universal types

CompanyProfile · MarketSnapshot · FinancialStatement · CorporateEvent · CorporateAction · Ownership · AnalystConsensus · NewsEvent · SectorKnowledge · MarketKnowledge

## Example

Yahoo `marketCap` / `trailingPE` / `revenueGrowth` become:

```yaml
CompanyKnowledge:
  Company: Infosys
  Valuation: { PE: 25.3 }
  Business: { Sector: Technology }
  Growth: { Revenue Growth: 19% }
  Metadata: { Source: Yahoo, Confidence: High, Version: N, Verified: true }
```

## Non-goals

No new collectors. No Learning Engine depth (6.3). No Evidence Graph wiring (6.4). No ops dashboards (6.5).

## Verification

```bash
cd knowledge-platform && pytest -q
```
