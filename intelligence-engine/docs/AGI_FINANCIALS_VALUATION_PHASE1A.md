# AGI Financials Valuation Intelligence: Phase 1A

## Scope

Phase 1A implements commercial-bank research intelligence only. It does not
apply bank formulas to NBFCs, insurers, asset managers, brokers, exchanges or
payments businesses. Classification is authoritative and fail-closed.

Current lifecycle status: **Operational / Not Investment Certified**.

Allowed use: research, scenario analysis, reverse valuation and Ask AGI
evidence context. Execution and automatic recommendations remain blocked.

## Reused AGI Systems

- AFE performs every numerical calculation from registered formulas.
- Company Intelligence Resolver remains the source of company classification.
- CRE supplies evidence-governed causal chains and contradictions.
- Ask AGI accesses the engine through `GET_BANK_VALUATION`.
- Existing thesis and knowledge systems remain authoritative; this phase does
  not create competing thesis or knowledge registries.

## Bank Knowledge Model

The versioned commercial-bank model contains 22 bank-specific KPI definitions,
including deposits, CASA, NIM, asset quality, credit cost, ROA, ROE, CET1 and
book value. Each definition records its formula, source hierarchy, causal role,
valuation role and limitations.

Supported valuation methods:

- P/B and P/TBV as primary methods
- normalized P/E as a cross-check
- justified P/B and residual income as secondary methods
- DDM only when payout evidence is suitable
- reverse valuation through implied ROE and implied growth

EV/EBITDA is explicitly marked inappropriate for commercial banks.

## Evidence Contract

Every critical input must contain a numeric value, source ID, reporting period
and availability date. Future-dated evidence produces a point-in-time violation.
Unproven company-name classification, raw numbers without provenance, invalid
capital or asset-quality inputs, and terminal growth at or above cost of equity
all fail closed.

Market prices may be paired with the latest already-available reported bank
fundamentals only through bank-specific AFE calculations. General AFE period
validation remains strict.

## Output Contract

The bank evaluator returns:

- current P/B and normalized P/E
- justified P/B and residual-income value
- historical and commercial-bank-only peer context
- market-implied ROE and growth
- bear, base and bull scenarios without invented probabilities
- ROE versus cost-of-equity sensitivity
- causal research context, monitoring variables and evidence gaps
- formula-level provenance and validation status

All outputs set `execution_eligible` to false in Phase 1A.

## Certification

Certification covers HDFC Bank, ICICI Bank, Axis Bank and SBI across 20 gates:
classification, business model, KPIs, statements, causal transmission, method
selection, multiple justification, reverse valuation, history, peers, scenarios,
sensitivity, PIT integrity, missing-data behavior, contradictions, accounting
quality, regulatory capital, client answers, adversarial behavior and provenance.

Passing automated gates does not self-certify the model. A named reviewer,
externally confirmed authorization and review evidence ID are all required, and
promotion remains a separate governance action.

## Database Migration

Apply `20260815213000_financials_valuation_intelligence.sql` in Supabase. It adds
versioned model, evidence and certification records with row-level security.
Do not label the live model certified until the four-company evidence packs and
authorized review have been persisted and independently checked.
