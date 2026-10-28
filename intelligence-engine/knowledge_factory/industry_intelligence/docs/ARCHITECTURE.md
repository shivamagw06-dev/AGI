# Institutional Industry & Value Chain Intelligence (IIVI) — AGIB v2.0 Sprint 4

## Naming

Not merely “Industry Intelligence”.

**Institutional Industry & Value Chain Intelligence** — the economic system around an industry: business model, value/supply chain, accounting language, KPIs, valuation, macro/government links, cycles, and institutional playbooks.

## Role

Soft Knowledge Factory package that teaches AGIB **how industries work**.

Frozen: Phase 1–7 reasoning, governance, Company / Corporate Event / Government / Sector / Macro / Historical Intelligence, Decision Quality, KF architecture.

## Package

```
knowledge_factory/industry_intelligence/
  docs/ collectors/ validators/ objects/ playbooks/
  value_chains/ supply_chains/ accounting/ valuation/ economics/
  dashboards/ apis/ registry/ tests/
```

## Coverage

Every Nifty 500 company maps to a structured `industry_id`.

Deep playbooks for high-impact industries (IT, banks, cement, steel, hospitals, …); Sector DNA soft-priors elsewhere with explicit UNKNOWN gaps.

## Future sprint (declared)

**Economic Network Graph** — company↔supplier/customer/competitor/commodity edges for chain-reaction questions (e.g. steel +20% → downstream impact). Depends on IIVI; does not change the reasoning engine.

## APIs

`/v1/industry/{dashboard,search,{name},playbook,value-chain,accounting,valuation,cycles,kpis}`
