# Phase 8.2A — Valuation Policy & Applicability Engine (VPAE)

**Status:** Implemented  
**Module:** `intelligence-engine/valuation_policy/`  
**Extends:** `valuation_terminal/sector_lens.py`  
**Version:** 8.2A

## Role

VPAE is AGIB’s **mandatory valuation decision layer**. It does **not** compute multiples.

It answers, for every company:

1. Which primary valuation methodology applies  
2. Which metrics are supporting  
3. Which metrics are hidden / unavailable  
4. Why  
5. How confident AGIB is  

Every valuation consumer must read policy before displaying or explaining a multiple.

```text
Company Master + Industry DNA + Instrument + Financials + DQIV
        ↓
Valuation Policy & Applicability Engine
        ↓
Primary / Supporting / Hidden / Status / Confidence
        ↓
Unified Valuation Engine → Terminal · Market · Ask · Portfolio · Research
```

## What changed vs sector_lens

`sector_lens` remains the **industry DNA baseline** (primary / supporting / suppressed).

VPAE adds:

| Signal | Effect |
|---|---|
| Instrument type (ETF / REIT / InvIT / …) | Hide equity multiples; NAV / Price-NAV primary |
| Negative earnings | Hide P/E; flip primary to EV/Sales (non-financials) |
| Extreme multiples | Status `EXTREME_VALUATION` (warning, never reject) |
| Missing book / EBITDA / revenue | `Unavailable` + `INSUFFICIENT_DATA` when primary blocked |
| DQIV checks | Wrong model, hidden without reason, instrument mismatch |

## API

```bash
GET /v1/valuation-policy/health
GET /v1/valuation/applicability/{symbol}
GET /v1/valuation/model/{symbol}
GET /v1/valuation/explanation/{symbol}
GET /v1/valuation/coverage/{symbol}
GET /v1/valuation/status/{symbol}
GET /v1/valuation/universe?sector=&instrument_type=&primary_model=&status=&confidence=
```

Node BFF mirrors these under `/api/intelligence/...`.

Admin UI: `/admin/valuation-policy`

## Output contract

```json
{
  "primary_model": "PRICE_TO_BOOK",
  "supporting_models": ["ROE", "ROA", "PE", "DIVIDEND_YIELD"],
  "hidden_models": ["EV_EBITDA", "EV_SALES"],
  "unavailable_models": [],
  "status": "BANKING_MODEL",
  "reason": "Deposit-taking financial institutions are primarily valued using Price-to-Book...",
  "confidence": "HIGH",
  "coverage": "FULL"
}
```

Statuses include: `VALID`, `LOSS_MAKING`, `EXTREME_VALUATION`, `INSUFFICIENT_DATA`, `ETF`, `REIT`, `INVIT`, `BANKING_MODEL`, `INSURANCE_MODEL`, `NBFC_MODEL`, `NOT_APPLICABLE`, `UNDER_REVIEW`.

## UVE gating

`valuation_engine.service.get_company_valuation` evaluates VPAE **before** attaching `meaningful` flags. The response includes a `policy` block. Terminal packs surface policy in explanation and table applicability notes.

## Ask AGI

`valuation_policy.ask.answer_for(symbol, question)` produces institutional prose for:

- “How should HDFC Bank be valued?”  
- “Why doesn’t Swiggy have a P/E?”

KUL `ValuationTerminalProvider` also prefers VPAE primary model + reason.

## Non-goals

- Does not compute PE/PB/EV multiples (UVE)  
- Does not compute historical series (Historical Valuation Engine)  
- Does not issue buy/sell recommendations  
- Does not replace `sector_lens` — it formalizes and extends it  

## Tests

```bash
cd intelligence-engine && python -m pytest valuation_policy/tests/test_vpae.py -q
```
