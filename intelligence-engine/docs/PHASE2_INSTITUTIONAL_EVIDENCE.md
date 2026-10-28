# Phase 2 — Institutional Evidence Intelligence

**Status:** Soft-wired under `institutional_reasoning/institutional_evidence/`  
**Architecture:** v1.0.1 LOCKED — not a new top-level engine  
**Depends on:** Phase 1 evidence-first execution governance

## Objective

Convert point-in-time financial data into **validated institutional evidence packs** that every framework executes against.

```
Financial Data → Institutional Evidence → Validated Evidence Packs → Frameworks → Committee
```

Frameworks never fetch. Frameworks consume packs through evidence contracts.

## Modules

| Module | Path | Priority |
| --- | --- | --- |
| Historical Intelligence | `historical.py` + `seeds.py` | ★★★★★ |
| Peer Intelligence | `peer.py` | ★★★★★ |
| Sector Intelligence | `sector.py` | ★★★★★ |
| Historical Analytics | `analytics.py` | ★★★★★ |
| Framework Binding | `pack.py` → `execution_governance.py` | ★★★★★ |
| Evidence Provenance | `provenance.py` | ★★★★☆ |
| Evidence Quality Engine | `quality.py` (reject &lt; 80) | ★★★★☆ |
| Business Quality | `business_quality.py` | ★★★★☆ |
| Accounting Quality | `accounting_quality.py` | ★★★★☆ |
| DCF Intelligence | `dcf.py` | ★★★★☆ |

## Pack shape (what frameworks receive)

```text
Company Infosys
Current PE 26.4
Historical PE 23.3
Historical Percentile 75%
Peer Median 23.5
Sector PE 29.5
ROIC 36%
Evidence Quality 97
Coverage 100%
```

Every metric carries: provider, timestamp, method, validated flag, quality score.

## Binding

`govern_answer(..., build_institutional_evidence=True)` (default) calls
`package_for_governance(entity)` and injects `packs["institutional_evidence"]`
before contract validation. Ask AGI (`app/ui/service.py`) uses the same path.

## Seeds vs live

- IT names (INFY/TCS/HCLTECH/WIPRO/TECHM) and NIFTYIT carry **institutional seed** PE history (FY17–FY26) with explicit provenance.
- PIL `it_services_v1` also exposes PE panels (FY22–FY26).
- Live Yahoo/DVC current PE is preferred when present in existing packs.
- Entities without series (e.g. NIFTYBANK PE) return transparent **insufficient** — never invented.

## Definition of Done

- Valuation frameworks execute from validated packs, not raw API responses.
- Historical, peer, and sector valuation metrics available for supported entities.
- Every metric carries provenance, freshness, and quality metadata.
- Frameworks consume evidence packs through contracts.
- “Is Nifty IT expensive versus history?” executes with computed evidence; missing series report insufficient.

## Tests

```bash
cd intelligence-engine
python3 -m pytest tests/test_phase1_acceptance.py tests/test_phase2_acceptance.py -q
```
