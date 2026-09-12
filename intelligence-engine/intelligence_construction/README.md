# Ask AGI Intelligence Construction V2

**Architecture status:** v1.0.1 LOCKED  
**Role:** Soft answer construction layer — not an engine, not a provider redesign.

## Mission

Every Ask AGI answer should become a richer institutional research brief by consuming validated intelligence already inside AGI:

CID → Company Analysis → Financial Intelligence → Company Monitor → KF → Academy → LEO → DVC → ECP → IRP → Institutional Answer

## Yahoo role

Yahoo remains an **internal** Market Data enrichment source (priority 40).  
Presentation never calls Yahoo and never mentions Yahoo / quoteSummary / yfinance / provider names.

## Soft wires

1. `company_analysis/cid_bridge.py` — bridge soft-enriched CID fields into analysis readers  
2. `intelligence_construction/brief.py` — assemble interpretive institutional brief  
3. `app/ui/service.py` — enrich Ask AGI `why` / executive / institutional_briefing  
4. `app/ui/sanitize.py` — scrub provider / Yahoo leakage from client payloads

## Entry

`intelligence_construction.production.package_for_ask_agi(...)`
