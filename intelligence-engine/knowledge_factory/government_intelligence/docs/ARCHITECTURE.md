# Institutional Government & Regulatory Intelligence (IGRI) — AGIB v2.0 Sprint 3

## Delivery phase: Phase 1 (high-impact only)

Sprint 3 does **not** model the entire government ecosystem.

### Phase 1 scope (exit gate)

1. **RBI** — monetary policy and banking regulation  
2. **Union Budget / Finance Ministry**  
3. **SEBI**  
4. **GST Council**  
5. **PLI schemes**  
6. **Import / export duties** (trade / customs)

These six areas account for most policy changes that materially affect listed Indian companies.

### Phase 2+ (architecture reserved, not required)

- MCA / Companies Act  
- Other industry regulators (IRDAI, TRAI, power, …)  
- State government policies  

Declared in registries / `fixtures/extensible_seeds.py`. Load later via `include_extensible=True` without redesign.

## Role

Soft Knowledge Factory package mapping Indian government & regulatory policy → sectors → industries → companies → macro → corporate events → portfolio context.

**Never** political opinion. **Never** policy forecasts. **Never** fabricate.

## Freeze locks

Phase 1–7 reasoning, Company Intelligence, Corporate Events, Decision Quality, KF architecture: frozen.

## Point-in-time

`announcement_date` / `effective_date` / `available_from`. Replay: `available_from <= as_of`.

## APIs (read-only)

`/v1/government/{dashboard,policies,policy/{id},search,rbi,sebi,budget,gst,pli,trade,timeline}`
