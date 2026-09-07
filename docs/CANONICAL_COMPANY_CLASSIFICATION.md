# Canonical Company Classification (Company Identity Service)

**Priority:** P0 — production blocker
**Rule:** Capital IQ is the single source of truth for company identity and
classification. No engine may infer a company's sector, industry, business
type, valuation framework, KPIs, or business model when the company exists in
the Capital IQ master.

## The bug this eliminates

Asking for **Axis Bank** returned:

```
Business Type:            Conglomerate
Enterprise Value Drivers: GRM, Production, Reserve Replacement, Refining Complexity
Industry DNA:             Banks
```

Root cause chain:

1. Capital IQ classifies Axis Bank as **Diversified Banks**.
2. Business Intelligence keyword-matched the label and hit its `diversified`
   alias before its `bank` alias, producing `conglomerate`.
3. `conglomerate` was mapped to `oil_gas` as a "soft fallback", so a bank was
   handed refining value drivers.

All three links are now removed. Classification comes from a canonical service
keyed on the Capital IQ **Primary Industry** — never from a description.

## Company Identity Service

`intelligence-engine/company_identity/`

```json
{
  "ticker": "AXISBANK",
  "company_name": "Axis Bank Limited",
  "primary_sector": "Financials",
  "primary_industry": "Diversified Banks",
  "business_type": "Universal Bank",
  "industry_dna": "banks"
}
```

| Module | Responsibility |
|---|---|
| `service.py` | Resolve identity by ticker, exact name, or company mention |
| `taxonomy.py` | Primary Industry → archetype / DNA / valuation framework / KPIs |
| `guard.py` | Cross-industry leakage and wrong-classification detection |
| `schema.py` | Immutable `CompanyIdentity` contract and the 11 primary sectors |

Resolution order: `valuation_consensus` (CapIQ Broker Estimates master) →
`institutional_knowledge_tables` (CapIQ screener exports). Coverage is **100%
of 2,987 companies**, with zero unmapped industries.

### Primary sectors

Only these eleven labels are ever emitted: Communication Services, Consumer
Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials,
Information Technology, Materials, Real Estate, Utilities.

### Mention resolution

A company binds only when it is unambiguous. Longest canonical name in the
question wins, then a unique prefix, then a single distinctive token.

| Mention | Binds |
|---|---|
| `Oil and Natural Gas Corporation Limited's business model?` | `ONGC` |
| `Indian Oil Corporation Limited` | `IOC` |
| `Apollo Hospitals` | `APOLLOHOSP` (not Apollo Micro Systems) |
| `Apollo`, `HDFC`, `Tata` | refused — ambiguous |
| `Air India` | refused — not in the listed universe |

## Company Metadata Router

`"Axis Bank primary sector"` is a stored Capital IQ field, not a research
question. It previously fell through Entity Intelligence to the Unknown Entity
Policy and was refused. Metadata questions now short-circuit ahead of
everything:

```
Question → Metadata Router → Company Identity Service → Capital IQ → answer
```

No Entity Intelligence gate, no KUL, no planner, no fusion, no composer. The
answer carries `intent="company_metadata"` and `sources=["company_identity"]`.

Recognised fields: sector, industry, industry classification, ticker,
exchange, website, currency, country, parent, company type, business type,
trading status, products, competitors, industry DNA. Headquarters, employees,
founded and ISIN are recognised but not carried in the current export, so they
return an honest "not in the export" answer rather than a guess.

A question only routes when the company is unambiguous. Resolution is tried in
order: full name in the question, unique prefix, ticker-shaped mention
(`ONGC`, `BPCL`, `HCLTech`), then curated market aliases (`Reliance`, `TCS`,
`DMart`). Ambiguous stems (`Apollo`, `HDFC`, `Tata`), abbreviation collisions
(`Sun Pharma`, which also abbreviates Sun Pharmaceutical Industries) and
uncovered names (`Air India`) fall through to the normal pipeline so
clarification and refusal still apply.

Analytical questions are never captured — anything containing why, how,
compare, thesis, valuation, risk, moat, consensus and similar goes to the
reasoning stack even when it mentions a metadata word.

## Precedence

```
Capital IQ Master → Industry DNA → Business Intelligence → Investment
→ Research → Market → Historical → Forecast
```

Fusion may enrich but never overwrite. Any fused line carrying another
industry's exclusive vocabulary is dropped, and a contaminated summary is
replaced. Every answer carries `diagnostics.company_identity` and
`diagnostics.classification_guard`.

## Automatic fails

Financials + GRM · Banks + Production · IT + Reserve Replacement ·
Hospitals + CASA · Retail + NIM · Airline + Oil Production ·
Conglomerate returned for Axis Bank · wrong Primary Sector · wrong Primary Industry.

Terms shared legitimately between allied families are not leaks — FMCG may use
SSSG, and a power producer may use plant load factor.

## API

| Route | Purpose |
|---|---|
| `GET /v1/company-identity/health` | Coverage and classification rate |
| `GET /v1/company-identity/{ticker}` | Full canonical identity |
| `POST /v1/company-identity/metadata` | Company Metadata Router lookup |
| `POST /v1/company-identity/validate` | Check text or a classification claim |

Node BFF mirrors these under `/api/intelligence/company-identity/*`.

## Release gate

`ask_product_test/run_canonical_classification_acceptance_v1.py` — 300
questions across all 11 sectors, verifying Primary Sector, Primary Industry,
Business Type, Industry DNA, Valuation Framework, KPI Dictionary and Business
Model consistency, including the 30 golden companies.

Current result: **300/300 (100%)**, golden **150/150**, sectors **11/11**,
cross-industry leakage **0**, wrong sector **0**, wrong industry **0**.

`ask_product_test/run_company_metadata_routing_acceptance_v1.py` — 68 checks
covering metadata answers, end-to-end Ask routing, analytical questions that
must not be captured, and ambiguous names that must fall through.

Current result: **68/68 (100%)** — metadata 40/40, pipeline 12/12,
analytical 10/10, fallthrough 6/6.

Unit contract: `company_identity/tests/test_company_identity.py`.
